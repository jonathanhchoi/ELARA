---
stage_id: "00-initialize"
title: "Initialize the project"
paper_steps: ["setup"]
core: true
interaction_profile: "normal"
long_running: false
prerequisites: []
required_inputs: ["repository root", "researcher instructions", "project/inputs/"]
declared_outputs: ["project/PROJECT_STATE.md", "project/PROJECT_CHARTER_vNNN.md", "project/ACCESS_MODEL_SNAPSHOT_vNNN.md", "project/INPUT_INVENTORY_vNNN.csv", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md", "project/runs/<run_id>/run_manifest.json"]
human_gate: "project-charter-approval"
next_stage: "01-conceive"
failure_routes: ["00-initialize"]
---

## Objective

Create or safely resume the single empirical legal research project in this repository. Establish its scope, immutable inputs, available data and model access, persistent machine-readable state, and append-only audit history before substantive research begins.

## Prerequisite checks

1. Work from the repository root and read AGENTS.md, PIPELINE.md, and the shared workflow contracts before acting.
2. Confirm that this repository contains no second active project. One clone represents one project; if the researcher wants a different project, tell them to make another copy rather than replacing this one.
3. Inspect project/ without modifying it. If PROJECT_STATE.md already exists, validate its front matter, read the active artifact versions and approvals, and resume or version this stage; never reinitialize or erase history.
4. Inventory every supplied file under project/inputs/ and any external path the researcher explicitly placed in scope. Do not move, rename, normalize, or edit an input.
5. If an instruction, input, or authorization record conflicts with the standing safeguards, stop with status waiting_for_user and identify the conflict precisely.

## Researcher decisions

The researcher must supply or confirm:

- the working project name and a short statement of the intended contribution;
- whether to run optional conception or begin with a researcher-selected question;
- the people, institutions, jurisdictions, time periods, and document types initially in scope;
- known confidentiality, license, terms-of-service, human-subjects, export, or institutional restrictions;
- available research databases, APIs, local software, models, subscriptions, and spending limits; and
- any facts or methods that must remain outside hosted models.

Do not invent these choices. Record unresolved choices as outstanding user inputs. A charter is not approved merely because a plausible default exists.

## Mode handoff

Run this stage in normal interactive mode. Do not start a Goal. Ask only for information that is genuinely missing after inspecting the repository. Explain that approval of the charter is a hard gate and that approval will be recorded verbatim.

## Work

1. Allocate a unique UTC run identifier in the shared-contract form YYYYMMDDTHHMMSSZ_00-initialize_rNNN. Never reuse a run directory.
2. If absent, create PROJECT_STATE.md and the three append-only ledgers using the shared schemas. If present, append or create new versions; never rewrite prior entries. If the copy has no .git directory, offer once — as a recorded researcher decision, never a silent action — to run git init with an initial commit so state and ledger changes gain change-tracking and accident protection; frame it as change-tracking, not tamper-proofing, and recommend it only for local, non-cloud-synced copies, since sync services (Google Drive, OneDrive, Dropbox) can corrupt mid-write appends and resurrect superseded versions.
3. Draft PROJECT_CHARTER_vNNN.md. Separate the research question, contribution, scope, exclusions, tentative unit of observation, intended audience, and success and stopping criteria. Mark every unconfirmed proposition as provisional.
4. Create ACCESS_MODEL_SNAPSHOT_vNNN.md from live inspection where possible. Record the date, platform, model name or user-visible identifier, execution surface, browsing and sub-agent availability, accessible databases, local runtimes, current limits, and any facts the researcher supplied rather than the agent verified. Do not expose secrets or copy credentials.
5. Create INPUT_INVENTORY_vNNN.csv with one row per input: immutable path, filename, media type, byte size, modification time, SHA-256 hash, source or supplier, access restriction, and inspection status. Hash the bytes without changing them. Record unreadable or missing items as typed gaps rather than silently omitting them.
6. In project/runs/<run_id>/run_manifest.json, record stage ID, timestamps, platform/model snapshot version, input artifact versions and hashes, planned outputs, and final disposition.
7. Append a RUN_LEDGER start row and, when work stops, a completion, failure, or waiting row with exact counts. Append any scope choices to DECISIONS.md and any departure from the canonical workflow to DEVIATIONS.md.
8. Present the charter and inventory summary to the researcher. If they already supplied a specific project, offer an explicit recorded skip of Stage 01; otherwise route to conception after approval.

## Artifacts

Create only the declared outputs. Use the next unused vNNN suffix for every versioned artifact. PROJECT_STATE.md is the sole mutable pointer to active versions; DECISIONS.md, RUN_LEDGER.md, and DEVIATIONS.md are append-only. Raw inputs remain in place and are never outputs.

## Verification

- Parse PROJECT_STATE.md front matter and confirm that schema_version, workflow_version, project_slug, current_stage, status, active_artifacts, approvals, outstanding_user_inputs, last_run_id, and updated_at are present and use the shared-contract types.
- Recompute a sample of input hashes and confirm that every in-scope input appears once in the inventory, including unreadable files and typed gaps.
- Confirm that every active artifact path exists, every new artifact is represented in the run manifest, and no prior version or input changed.
- Check that the access snapshot distinguishes live-verified facts from researcher-reported facts and contains no token, key, password, or confidential text.
- Self-review the charter against the researcher's actual instructions and disclose every file created or changed.

## State transition

At execution start, set current_stage to 00-initialize, status to running, last_run_id to the new run ID, and updated_at to the current UTC time, then append the matching ledger start. After the artifacts verify, update active_artifacts to their exact versioned paths, set status to awaiting_approval, leave approvals unchanged until a decision exists, and list the exact project-charter-approval request and unresolved confirmations in outstanding_user_inputs. Make no next-stage transition until the researcher explicitly approves the charter.

On approval, append the decision with timestamp and the researcher's words, add a version-pinned approval record linked to that decision, clear only the resolved inputs, set updated_at, and set status to ready. The default current_stage becomes 01-conceive. If the researcher explicitly supplies and selects a project and elects to skip conception, record that deviation and route to 02-preemption-review without fabricating Stage 01 artifacts.

## Next-stage handoff

Tell the researcher which charter and inventory versions are active. If conception is needed, provide the exact handoff: run the 01-conceive stage and supply prior papers, a CV, research notes, or a corrections note. If conception was explicitly skipped, provide the exact handoff to 02-preemption-review with the selected question, intended data, method, and claimed contribution, and note that Stage 02 begins with a bounded smoke screen — corpus access plus the Stage 01 selection tests — before any exhaustive searching, because the researcher-supplied project has not yet passed those tests.
