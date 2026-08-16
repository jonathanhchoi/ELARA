---
stage_id: "00-initialize"
title: "Initialize the project"
paper_steps: ["setup"]
core: true
interaction_profile: "normal"
long_running: false
prerequisites: []
required_inputs: ["repository root", "researcher instructions", "project/inputs/", "project/inputs/existing/ (adoption path only: the researcher's existing project materials)"]
declared_outputs: ["project/PROJECT_STATE.md", "project/PROJECT_CHARTER_vNNN.md", "project/ACCESS_MODEL_SNAPSHOT_vNNN.md", "project/INPUT_INVENTORY_vNNN.csv", "project/PUBLICATION_PROFILE_vNNN.md", "project/artifacts/adoption_map_vNNN.md", "project/artifacts/imported_vNNN/", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md", "project/runs/<run_id>/run_manifest.json"]
human_gate: "project-charter-approval"
next_stage: "01-conceive"
failure_routes: ["00-initialize"]
---

## Objective

Create or safely resume the single empirical legal research project in this repository. Establish its scope, immutable inputs, available data and model access, persistent machine-readable state, and append-only audit history before substantive research begins. Two paths: the **fresh path** (`start`) for a new project, and the **adoption path** (`adopt`) for a project that already exists in some form, which imports what exists, records what the researcher vouches for, and lands the pipeline at the first stage that still needs to run.

## Prerequisite checks

1. Work from the repository root and read AGENTS.md, PIPELINE.md, and the shared workflow contracts before acting.
2. Confirm that this repository contains no second active project. One clone represents one project; if the researcher wants a different project, tell them to make another copy rather than replacing this one.
3. Inspect project/ without modifying it. If PROJECT_STATE.md already exists, validate its front matter, read the active artifact versions and approvals, and resume or version this stage; never reinitialize or erase history.
4. Inventory every supplied file under project/inputs/ and any external path the researcher explicitly placed in scope. Do not move, rename, normalize, or edit an input.
5. Choose the path. Use the adoption path when the researcher said `adopt`, when project/inputs/existing/ is populated, or when the researcher describes work already done (a question already chosen and researched, a codebook, coded data, results, a draft, a referee letter). Otherwise use the fresh path. If unsure, ask one question: "Is this a new project, or do you already have work you want to bring in?"
6. Check the environment before the interview: run `python scripts/doctor.py --json --platform <active-platform>`. If it fails because Python 3.10+ or `jsonschema` is missing, give the researcher the two install commands from README.md, set status waiting_for_user, and stop; do not proceed on a broken environment.
7. If an instruction, input, or authorization record conflicts with the standing safeguards, stop with status waiting_for_user and identify the conflict precisely.

## Researcher decisions

The researcher must supply or confirm:

- the working project name and a short statement of the intended contribution;
- whether to run optional conception or begin with a researcher-selected question;
- the people, institutions, jurisdictions, time periods, and document types initially in scope;
- known confidentiality, license, terms-of-service, human-subjects, export, or institutional restrictions;
- available research databases, APIs, local software, models, subscriptions, and spending limits;
- any facts or methods that must remain outside hosted models; and
- optionally, the intended venue and audience, so the publication profile can be created now rather than at Stage 17.

On the adoption path the researcher also decides: which preset (or custom landing) to use; which gates to approve on their own word (any gate may be asserted); which existing files to import as artifacts; and whether the limitations the adoption map lists are acceptable.

Do not invent these choices. Record unresolved choices as outstanding user inputs. A charter is not approved merely because a plausible default exists.

## Mode handoff

Run this stage in normal interactive mode. Do not start a Goal. Ask only for information that is genuinely missing after inspecting the repository, one question at a time, in plain language, with an example answer. Accept "don't know" and record it as an outstanding input rather than choosing a default. Keep the interview under ten questions unless the researcher wants more. Explain that approval of the charter is a hard gate and that approval will be recorded verbatim.

## Orientation (first session)

Before the first question, and whenever the researcher asks for `help` or `tour`, give a short orientation (under 250 words) that covers: what ELARA does (walks one empirical legal research project from question to replication package, with optional publication stages) and does not do (choose the question, write the first draft, or advance past a decision without the researcher); the six paper steps and how they map to the twenty stages; that a stage ends at a gate where the researcher decides, that silence is never approval, and that a decision is recorded verbatim; that Stages 02, 03, and 11 are long-running and the researcher can walk away and later type `resume`; the commands (`start`, `adopt`, `resume`, `status`, `help`, and the manuscript utilities `elr-proofread`, `elr-add-citations`, `elr-apply-markup`); and where the publication profile lives. Then say what will happen next in this session and roughly how long it takes.

## Work

Fresh path (`start`):

1. Allocate a unique UTC run identifier in the shared-contract form YYYYMMDDTHHMMSSZ_00-initialize_rNNN. Never reuse a run directory.
2. If absent, create PROJECT_STATE.md and the three append-only ledgers using the shared schemas. If present, append or create new versions; never rewrite prior entries. If the copy has no .git directory, offer once — as a recorded researcher decision, never a silent action — to run git init with an initial commit so state and ledger changes gain change-tracking and accident protection; frame it as change-tracking, not tamper-proofing, and recommend it only for local, non-cloud-synced copies, since sync services (Google Drive, OneDrive, Dropbox) can corrupt mid-write appends and resurrect superseded versions.
3. Draft PROJECT_CHARTER_vNNN.md. Separate the research question, contribution, scope, exclusions, tentative unit of observation, intended audience, and success and stopping criteria. Mark every unconfirmed proposition as provisional.
4. Create ACCESS_MODEL_SNAPSHOT_vNNN.md from live inspection where possible. Run `python scripts/doctor.py --json --platform <active-platform>` and preserve its secret-free output as a fenced `capability_record` JSON block in the snapshot; if the command or a field is unavailable, record that typed gap rather than guessing. Record the date, platform and host version, model name or user-visible identifier, execution surface, repository-skill discovery, Goal or dynamic-workflow and sub-agent availability, browsing, configured MCP or other external integrations, permission or sandbox controls, accessible databases, local runtimes and dependency versions, current limits, and any facts the researcher supplied rather than the agent verified. Do not expose secrets or copy credentials. Treat a changed host, model route, permission profile, or integration after approval as capability drift requiring a new snapshot version and downstream authorization review where data exposure could change.
5. Create INPUT_INVENTORY_vNNN.csv with one row per input: immutable path, filename, media type, byte size, modification time, SHA-256 hash, source or supplier, access restriction, and inspection status. Hash the bytes without changing them. Record unreadable or missing items as typed gaps rather than silently omitting them.
6. In project/runs/<run_id>/run_manifest.json, record stage ID, timestamps, platform/model snapshot version, input artifact versions and hashes, planned outputs, and final disposition.
7. Append a RUN_LEDGER start row and, when work stops, a completion, failure, or waiting row with exact counts. Append any scope choices to DECISIONS.md and any departure from the canonical workflow to DEVIATIONS.md.
8. If the researcher already knows the venue and audience, offer to create project/PUBLICATION_PROFILE_vNNN.md now from workflow/templates/publication_profile_template.md from their answers and pin it in state as publication_profile; otherwise say that Stage 17 will ask. Never fill the profile with guesses.
9. Present the charter and inventory summary to the researcher. If they already supplied a specific project, offer an explicit recorded skip of Stage 01; otherwise route to conception after approval.

Adoption path (`adopt`), in addition to fresh-path steps 1, 2, 4, 5, 6, 7, and 8:

A1. Ask what already exists, one item at a time, from this checklist: a research question and claimed contribution; a literature or preemption review; a feasibility assessment; hypotheses and methods; a codebook, schema, or coding prompt; data authorization (license, terms, IRB or ethics); an adversarial review; a pilot; a preregistration (with its date and external identifier if any); a corpus; coded data; interpretive verification; human validation data; analysis code and results; robustness checks; a replication package; a manuscript draft; referee or editor letters. Ask the researcher to place the files under project/inputs/existing/ (or to name an external path for anything too large to copy, which is inventoried by path and hash). Inventory and hash them like every other input.
A2. Propose a preset from the inventory and confirm it with the researcher, or agree a custom landing: **question only** (lands at 02-preemption-review; Stage 01 recorded as skipped); **design in hand** (methods, codebook, schema, or prompt exist; lands at 06-data-authorization, unless authorization is asserted, in which case 07-adversarial-review, or 08-pilot if that is asserted too); **data in hand** (coded data exist; lands at 12-interpretive-verification, or 13-human-validation if a verification exists and is asserted, or 14-analysis-and-correction if human validation exists and is asserted); **results in hand** (analysis and results exist; lands at 16-replication-package, or 17-integrate-manuscript if a package exists and is asserted); **publication only** (a draft, perhaps with a referee letter; Stages 01–16 recorded as not run by ELARA; lands at 17-integrate-manuscript if results are to be integrated, otherwise 18-cite-check; the manuscript utilities are available at once). The landing stage is the first stage whose gate the researcher does not assert or whose artifacts do not exist.
A3. Build project/artifacts/adoption_map_vNNN.md: one row per stage 01–19 with status (have / partial / missing / not run by ELARA / not applicable), the imported file or files that satisfy it, the gate and its basis (asserted, verified, or none), and notes. Mark as partial anything the landing stage's prerequisite checks would want but the import lacks (for example coded data without evidence records or a schema, or a validation sample without inclusion probabilities), so the landing stage builds the missing derivative as a versioned artifact rather than silently skipping the check. State the facts adoption cannot supply, if they apply: preregistration timing (if analyses ran before any preregistration, or none exists, the analyses are labeled not preregistered unless a dated record is imported); held-out purity (if the researcher cannot list which units touched prompt or codebook tuning, Stage 13 reports the sample as not held out); audit separation (previously audited work is re-audited when Stages 12 or 18 run; imported audits are recorded as prior audits); and the coder model and version, if unknown.
A4. Import the usable files by copying them, unchanged, into project/artifacts/imported_vNNN/ (keeping their names), record each file's role, source path, and SHA-256 hash in the run manifest, and pin each imported artifact in active_artifacts under the logical name a downstream stage will look for (for example codebook, coding_schema, coding_dataset, corpus_manifest, analysis_results, manuscript, publication_profile). Downstream stages resolve pinned paths, not fixed filenames.
A5. Record approvals. For every gate the researcher chooses to assert, append a DECISIONS.md entry quoting the researcher's words, and add a version-pinned approval record with decision approved and basis researcher-asserted, listing the imported artifact hashes it rests on. Any gate may be asserted; the point is to make the researcher's existing judgment usable, not to re-litigate it. Gates the researcher does not assert stay open, and the landing stage cannot precede them. For the publication-only preset, record Stages 01–16 as not run by ELARA rather than as approved.
A6. Append one standing DEVIATIONS.md entry: adopted on this date at the landing stage; which stages were not run by ELARA; which approvals are researcher-asserted; the facts adoption could not supply; and that ELARA's own verification begins at the landing stage. Put the same summary in the charter.
A7. Set current_stage to the landing stage and status to ready, with active_artifacts pinned to the imported versions and the adoption map, then give the exact next command. Later stages treat imported artifacts pinned in state as satisfying their required inputs and asserted approvals as satisfying their gate prerequisites; they still verify what they can (hashes, counts, formats) and record what they cannot as a limitation rather than refusing to run.

## Artifacts

Create only the declared outputs. Use the next unused vNNN suffix for every versioned artifact. PROJECT_STATE.md is the sole mutable pointer to active versions; DECISIONS.md, RUN_LEDGER.md, and DEVIATIONS.md are append-only. Raw inputs remain in place and are never outputs. On the adoption path, project/artifacts/imported_vNNN/ holds unchanged copies of the researcher's existing files and project/artifacts/adoption_map_vNNN.md records what each one satisfies.

## Verification

- Parse PROJECT_STATE.md front matter and confirm that schema_version, workflow_version, project_slug, current_stage, status, active_artifacts, approvals, outstanding_user_inputs, last_run_id, and updated_at are present and use the shared-contract types.
- Recompute a sample of input hashes and confirm that every in-scope input appears once in the inventory, including unreadable files and typed gaps.
- Confirm that every active artifact path exists, every new artifact is represented in the run manifest, and no prior version or input changed.
- Check that the access snapshot contains a parseable `capability_record`, distinguishes live-verified facts from researcher-reported facts, records every unavailable capability as a typed gap, and contains no token, key, password, or confidential text.
- Self-review the charter against the researcher's actual instructions and disclose every file created or changed.
- On the adoption path: confirm every imported file is an unchanged copy with a recorded hash, every asserted approval quotes the researcher and names its basis as researcher-asserted, the adoption map covers Stages 01–19 with a status for each, the standing deviation entry exists, and the landing stage's gate prerequisites are all either asserted or verified.

## State transition

At execution start, set current_stage to 00-initialize, status to running, last_run_id to the new run ID, and updated_at to the current UTC time, then append the matching ledger start. After the artifacts verify, update active_artifacts to their exact versioned paths, set status to awaiting_approval, leave approvals unchanged until a decision exists, and list the exact project-charter-approval request and unresolved confirmations in outstanding_user_inputs. Make no next-stage transition until the researcher explicitly approves the charter.

On approval, append the decision with timestamp and the researcher's words, add a version-pinned approval record linked to that decision, clear only the resolved inputs, set updated_at, and set status to ready. The default current_stage becomes 01-conceive. If the researcher explicitly supplies and selects a project and elects to skip conception, record that deviation and route to 02-preemption-review without fabricating Stage 01 artifacts. On the adoption path, the charter approval also covers the adoption map and the asserted approvals; current_stage becomes the agreed landing stage.

## Next-stage handoff

Tell the researcher which charter and inventory versions are active. If conception is needed, provide the exact handoff: run the 01-conceive stage and supply prior papers, a CV, research notes, or a corrections note. If conception was explicitly skipped, provide the exact handoff to 02-preemption-review with the selected question, intended data, method, and claimed contribution, and note that Stage 02 begins with a bounded smoke screen — corpus access plus the Stage 01 selection tests — before any exhaustive searching, because the researcher-supplied project has not yet passed those tests. On the adoption path, name the landing stage, the imported artifacts it will use, the approvals that were asserted, the limitations the adoption map lists, and the exact command to run next (`resume` runs the landing stage; the manuscript utilities are available immediately if a draft was imported).
