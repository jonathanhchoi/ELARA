# Artifact and state contract

This contract makes the pipeline resumable, auditable, and non-destructive. It
applies to every stage and overrides convenient but lossy file-writing habits.

## 1. Paths and control files

- All research inputs, state, runs, and outputs live under `project/` at the
  working root `storage.md` resolves; exported copies are not a second state.
- Besides its `declared_outputs`, any writable stage, utility, setup, or
  recovery may write these operational records, which cannot change inputs or
  results: `project/ELARA_STORAGE.json` in both roots, `project/storage/` in
  the local root, verified copies in the recorded `ELARA_Results/` folder, and
  `project/kit_issues/kit_issue_<UTC timestamp>.md` reports under "When
  something breaks" in `operational-recovery.md`.
- `project/PROJECT_STATE.md` is the only mutable routing pointer.
  `project/DECISIONS.md`, `project/RUN_LEDGER.md`, and `project/DEVIATIONS.md`
  are append-only: correct a record by appending one that supersedes it.
- A stage writes only its `declared_outputs` and the records above; logs,
  caches, prompts, and raw responses belong inside a declared run directory. A
  declared output written `path (condition)` is produced only under that
  condition; `(after the <gate> gate)` means once the researcher decides that
  gate. `scripts/stage_check.py` requires every other declared output, and
  those conditional ones once their gate is approved.

## 2. Runs

A run ID is `YYYYMMDDTHHMMSSZ_<stage-id>_rNNN` (for example
`20260710T184233Z_08-pilot_r001`), created in UTC before execution writes
research output, with `r001` incremented if the prefix exists; never reuse one.
Run material lives under `project/runs/<run_id>/`, which is immutable once the
run closes. Set `last_run_id`, append a started entry to `RUN_LEDGER.md`, and
append the closing facts without replacing it. Besides what `guardrails.md` §6
lists, archive tool and environment versions and the stage-start
`kit_update_check.json`, which names the ELARA
commit without rewriting the historical `workflow_version`.

## 3. Artifact versions

Every rerunnable or approvable artifact carries a three-digit version before
the extension (`codebook_v002.md`), and a versioned directory is `name_vNNN/`.
Begin at `v001` and select the next
unused integer; never overwrite a file because a prior run failed or was not
approved. Only `PROJECT_STATE.md`, the three logs, kit README and instruction
files, and inventoried input filenames are unversioned. An artifact becomes
active only after verification: record its logical name and exact path in
`active_artifacts`, and use that path downstream, never "latest" globbing.

For a formatted narrative report to the researcher, the default active artifact
is a PDF compiled from a versioned LaTeX source, kept with its build source and
log; render and inspect every page before activation. Use Word, Markdown, HTML,
or another format only when the researcher expressly asks for it or the active
publication profile records that preference. CSV, JSON, code, schemas, ledgers,
and manifests stay in their native formats.

## 4. Immutable inputs

Stage 00 inventories each file in `project/inputs/` with path, size, hash, media
type, provenance, and authorization status. Never rename, move, normalize, OCR
in place, or overwrite an input; derivatives are versioned outputs citing the
source hash, and a corrected input gets a new name, inventory row, and
superseding decision. For external data, archive a stable snapshot when
authorized, or record its immutable identifier, retrieval procedure, checksum,
and access limits. A changed input set is a design event, not housekeeping.

## 5. State front matter

`PROJECT_STATE.md` front matter routes; the body is prose. Keys:

- `schema_version` (quoted; older schemas stay valid), `workflow_version`, and
  `project_slug` (quoted after charter approval, otherwise `null`).
- `usage` (optional): `pipeline` (absent means this) or `tools`.
- `checkpoints` (optional): `none` (the default), `stages`, `plans`, or `all`;
  it adds pauses and never removes a gate.
- `failure_handling` (optional): `autonomous` or `interactive`, for unit
  failures in the Stage 11 run only (`guardrails.md` §11).
  Absent means `autonomous`. It never relaxes a gate, budget, authorization, deviation,
  blind adjudication, or researcher review. Changing any of these three is a
  recorded decision.
- `current_stage` and `status`: `ready`, `paused`, `running`,
  `awaiting_approval`, `waiting_for_user`, `failed`, `complete`, or
  `superseded`. Any other value is malformed: stop and report it.
- `active_artifacts` (names to exact paths, or path and hash records),
  `approvals`, `outstanding_user_inputs`, `last_run_id`, and `updated_at`.
- `run_checkpoint` (optional): `path` and `sha256` of a payload-free
  checkpoint, verified on resume; evidence, not permission to launch.

`ready`, `running`, and `complete` carry no unresolved requests;
`waiting_for_user` and `awaiting_approval` name one; `paused` marks a part set
aside under "When something breaks" while other work continues. Write no
project file during a Plan phase. Set the terminal state only after artifacts
and counts verify, archiving each outgoing state file under the run first. Write state and ledgers as UTF-8
without a byte-order mark (Windows PowerShell 5 adds one with `-Encoding
utf8`). An interrupted `running` state is a resumable fact, not permission to
restart.

## 6. Version-pinned approvals

An approval holds the gate ID and decision (`approved`,
`conditionally-approved`, `rejected`, `invalidated`); its basis (`verified`, or
`researcher-asserted` when recorded on Stage 00's adoption path on the
researcher's word); the decision ID; the exact paths and SHA-256 hashes
reviewed; the run ID, researcher label, and UTC time; the decision text; and
any conditions, registration identifier, or limitations. It covers only those versions. When a dependency
changes, mark it `invalidated` with the reason and keep it.

## 7. Dependency invalidation

| Changed item | Required invalidation and return |
|---|---|
| Question, scope, population, or selected candidate | All downstream approvals; stages 01–04. |
| Hypothesis, estimand, sampling, inference, or analysis plan | Design freeze, pilot, preregistration, results; stage 04. |
| Codebook, schema, measurement rules, or unit space | Freeze, pilot, preregistration, scale-up, validation, analysis; stage 05. |
| Model route, license basis, confidentiality, or IRB/ethics status | Data authorization and every output under that route; stage 06. |
| Adversarial-review resolution or pilot configuration or result | Design freeze or pilot acceptance; stage 07 or 08. |
| Frozen or preregistered artifact | Pause, log a deviation, record an amendment at stage 09 first. |
| Corpus population, coverage, provenance, exclusions, OCR, deduplication | Stage 10, and 06 or 09 if authorization or scope is affected. |
| Validation sample, human coding, adjudication, or error model | Validation acceptance and corrected analysis; stage 13. |
| Analysis or robustness code | Rebuild stages 14–16 and dependent publication files. |
| Skeleton, manuscript, or citation support | New version; repeat stages 17–20 as applicable. |

Never narrow an invalidation because rerunning is expensive; if the effect is
uncertain, treat it as material and ask.

## 8. Deviations and amendments

Log a deviation as soon as work departs from an approved, frozen, or
preregistered artifact: run, versions, time, description, cause, effect,
action, and researcher disposition. One that could change the question,
population, hypotheses, estimand, measurement, units, sampling, exclusions,
authorization, model route, validation, analysis, or interpretation is
material (borderline cases are the researcher's call) and stops affected work
until the amendment is approved; one found late marks the work affected and
routes back. Never make a deviation look planned, and record a registration
identifier only after the researcher completes that action.

## 9. Audits, corrections, and replication

An audit writes a versioned findings file and never alters what it audits; the
correction is a new version in the failure-route stage. Raw observations, human
codes, adjudications, exclusions, and corrections stay distinct, and a
corrected row points to the one it supersedes. "No finding" and "not processed"
are different values, and gap rows stay in the denominators. Stage 16's package
reproduces every reported number from declared inputs, as a fresh agent
verifies; restricted material gets a truthful access procedure, and the package
is never patched by hand.
