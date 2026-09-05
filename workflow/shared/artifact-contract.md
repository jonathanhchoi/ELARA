# Artifact and state contract

This contract makes the pipeline resumable, auditable, and non-destructive. It
applies to every stage and overrides convenient but lossy file-writing habits.

## 1. Paths and control files

- All research inputs, state, runs, and outputs live under `project/`.
- Canonical prompts, wrappers, scripts, tests, and repository instructions are
  kit infrastructure. Research stages read them but do not alter them.
- `project/PROJECT_STATE.md` is the only mutable routing pointer.
- `project/DECISIONS.md`, `project/RUN_LEDGER.md`, and
  `project/DEVIATIONS.md` are append-only records. Correct a record by appending a
  superseding record that links to it; never edit or delete the original.
- A stage may write only paths listed in its `declared_outputs`. Incidental logs,
  caches, prompts, and raw responses must be covered by a declared run directory
  or declared output path.

## 2. Run identity

Create a run ID before any execution phase writes research output:

```text
YYYYMMDDTHHMMSSZ_<stage-id>_rNNN
```

Example:

```text
20260710T184233Z_08-pilot_r001
```

Rules:

- Use UTC and a zero-padded timestamp.
- Copy the canonical zero-padded `stage_id` exactly.
- Start the attempt suffix at `r001`; increment it if the timestamp/stage prefix
  already exists. Never reuse a run ID, including after failure.
- Store run-local material under `project/runs/<run_id>/` unless the stage
  declares a stricter location. Once a run closes, its directory is immutable.
- Set `last_run_id` to the open run and append a started entry to
  `RUN_LEDGER.md`. On completion or failure, append the closing facts; do not
  replace the opening entry.

At minimum, archive the run's canonical prompt version, rendered prompt, input
paths and hashes, model/provider/version, parameters, tool and environment
versions, raw responses, parsed responses, validation results, timestamps,
errors, and exact reconciliation counts.

## 3. Artifact versions

Every rerunnable or approvable artifact uses a three-digit version suffix before
the extension:

```text
methods_plan_v001.md
codebook_v002.md
pilot_outputs_v003.parquet
corpus_manifest_v001.csv
```

Use `name_vNNN/` for a versioned directory. Begin at `v001` and select the next
unused integer. Never infer that an existing file may be overwritten because a
prior run failed or was not approved.

Unversioned exceptions are limited to:

- the mutable `PROJECT_STATE.md` router;
- the three append-only project logs;
- README/instruction files supplied by the kit; and
- immutable user input filenames, whose identity is fixed by an inventory entry
  and hash.

An artifact becomes active only after verification. Record its logical name and
exact repository-relative path in `active_artifacts`; downstream work must use
that pinned path, not “latest” globbing or a filename guess.

### Default format for researcher-facing reports

When a stage produces a formatted narrative report for the researcher, the
default active artifact is a PDF compiled from a versioned LaTeX source. Keep
the auditable Markdown or other structured build source and the generated
`.tex` file with the run record. Compile the PDF, archive the build log, render
every page, and inspect it before activation. Do not treat a source file alone
as the finished report.

Use Word, Markdown, HTML, or another researcher-facing format only when the
researcher expressly asks for it or an active publication profile records that
preference. Record the preference and build the requested format from the same
immutable source. Machine-readable evidence and working artifacts such as CSV,
JSON, JSONL, code, schemas, ledgers, and manifests remain in their appropriate
native formats; this PDF default does not convert them into page documents.

## 4. Immutable inputs

- Stage 00 inventories each file in `project/inputs/` with a repository-relative
  path, byte size, cryptographic hash, media type, provenance supplied by the
  researcher, and authorization status.
- After inventory, do not rename, move, normalize, OCR in place, edit metadata,
  or overwrite an input. Derivatives are versioned outputs and retain the source
  input's path and hash.
- A corrected or replacement input receives a new filename and a new inventory
  row. Append a decision identifying which prior input it supersedes.
- For externally stored data, archive a stable snapshot when authorized. If only
  a reference is permitted, record the immutable identifier/version, retrieval
  procedure, hash or provider checksum when available, and access restriction.
- A changed input set is a design event, not housekeeping. Reassess scope,
  authorization, preregistration, and all dependent outputs.

## 5. State front matter

`PROJECT_STATE.md` front matter is machine-readable. Preserve these keys and
types:

- `schema_version`: quoted state-schema version (`1.1` adds the optional
  `usage` key, `1.2` the optional `checkpoints` key, `1.3` the optional
  `failure_handling` key; files written under earlier schemas remain valid).
- `workflow_version`: quoted pipeline release version.
- `project_slug`: quoted stable slug after Stage 00 charter approval, or `null`
  throughout the untouched, running, waiting, and pre-approval Stage 00 states.
  Use the surrounding state fields—not a null slug alone—to distinguish a blank
  distribution template from an in-progress project.
- `usage` (optional): the usage mode Stage 00 records after its orientation —
  `pipeline` when the researcher follows the whole workflow stage by stage (the
  router continues into the next stage when one ends, unless a stop condition in
  `workflow/shared/guardrails.md` section 11 holds), or `tools` when the researcher
  runs specific stages and utilities from the menu in `PIPELINE.md` on request
  (the router offers the menu instead, and `resume` reopens it). Absent means
  `pipeline`. Changing it later is a recorded decision. Usage mode never alters
  a prerequisite, gate, or approval; it decides only what is offered next.
- `checkpoints` (optional): how often the researcher wants to be consulted
  beyond the gates — `none` (low-touch, the default: the assistant continues
  between stages and executes its plans without waiting, per
  `workflow/shared/guardrails.md` §11), `stages` (pause for agreement before
  each next stage), `plans` (pause for approval after each plan, before
  executing it), or `all` (both). Absent means `none`. Stage 00 records the
  researcher's answer; changing it later is a recorded decision. A checkpoint
  preference adds pauses; it never removes a gate.
- `failure_handling` (optional): how unit-level failures during the Stage 11
  coding run are dispositioned — `autonomous` (the default: the assistant
  decides each one under the frozen rules, records it in the run's
  failure-decisions log under the run directory, keeps the run going, and
  presents the complete digest at the end of the run and at the next gate,
  per `workflow/shared/guardrails.md` §11) or `interactive` (the assistant
  pauses at the batch or validation checkpoint where it detects failures and
  asks the researcher to dispose of each, in one batched message per
  checkpoint). Absent means `autonomous`. Stage 00 records the researcher's
  answer; changing it later is a recorded decision, and the Stage 08
  interview confirms or changes it before the full run. The mode governs
  only the disposition of individual failed units under rules already
  frozen; it never relaxes a gate, budget stop, authorization requirement,
  deviation handling, blind adjudication, or a review a stage assigns to the
  researcher.
- `current_stage`: quoted canonical stage ID.
- `status`: one of `ready`, `paused`, `running`, `awaiting_approval`,
  `waiting_for_user`, `failed`, `complete`, or `superseded`. Treat any other
  value as malformed state: stop and report a state-recovery issue rather than
  guessing what it meant.
- `active_artifacts`: mapping from logical artifact names to exact versioned
  repository-relative paths (or structured path/hash records once populated).
- `approvals`: mapping from gate IDs to version-pinned approval records.
- `outstanding_user_inputs`: array of concrete unanswered requests.
- `last_run_id`: quoted run ID or `null`.
- `updated_at`: quoted UTC ISO 8601 timestamp or `null` before first write.

The body below the front matter is prose for humans; the front matter alone
routes.

Do not write any project file during a Plan phase. In an execution-capable
handoff, transition state immediately before opening a run; checkpoint it during
long runs; and write the terminal state only after artifacts and counts verify.
Before each rewrite of `PROJECT_STATE.md` during a run, archive the outgoing
file under the open run directory (for example
`project/runs/<run_id>/state_history/`), so a botched or interrupted write has a
mechanical recovery source. Write state and ledger files as UTF-8 without a
byte-order mark, using LF newlines; a BOM breaks the state parser, and Windows
PowerShell writes one by default with `-Encoding utf8` under PowerShell 5.
An interrupted `running` state and an unclosed ledger entry are resumable facts,
not permission to discard or restart the run.

## 6. Version-pinned approvals

An approval record must include:

- gate ID and decision (`approved`, `conditionally-approved`, `rejected`, or
  `invalidated`);
- basis: `verified` when the gate's stage ran under ELARA and its artifacts were
  verified, or `researcher-asserted` when the approval was recorded on the
  adoption path of Stage 00 on the researcher's word, resting on imported
  artifacts. Any gate may be researcher-asserted; the basis is recorded so that
  reports and the replication package can say which checks ELARA performed;
- decision ID linking to the append-only decision log;
- exact artifact paths and SHA-256 hashes reviewed;
- run ID, researcher identity label as provided, and UTC decision time;
- the researcher's decision text or a faithful quotation; and
- conditions, expiration, external registration identifier, or limitations where
  applicable.

Approval applies only to the listed versions. It does not float to a later
`_vNNN` file, even if a filename or summary looks similar. When a dependency
changes, mark the approval `invalidated` with time, reason, and superseding
decision link. Keep the invalidated record in state/history and route back to the
relevant gate.

## 7. Dependency invalidation

At minimum, apply these rules:

| Changed item | Required invalidation and return |
|---|---|
| Project question, scope, population, or selected candidate | Invalidate all downstream approvals; return to stages 01–04 as appropriate. |
| Hypothesis, estimand, sampling, inference, or analysis plan | Invalidate methods/design freeze, pilot, preregistration, and downstream results; return to stage 04. |
| Codebook, schema, prompt measurement rules, edge-case rule, or unit space | Invalidate codebook/design freeze, pilot, preregistration, scale-up, validation, and analysis; return to stage 05. |
| Model/provider route, license basis, confidentiality treatment, or IRB/ethics status | Invalidate data authorization and every output produced under that route; return to stage 06. |
| Adversarial-review resolution or pilot configuration/result | Invalidate design freeze or pilot acceptance and downstream freeze; return to stage 07 or 08. |
| Frozen or preregistered artifact | Pause execution, log a deviation, return to stage 09, and record an amendment before affected work. |
| Corpus population, coverage, provenance, exclusions, OCR treatment, or deduplication rule | Return to stage 10; also return to stages 06 or 09 if authorization or preregistered scope is affected. |
| Human-validation sample, coding, adjudication, or error model | Invalidate validation acceptance and corrected analysis; return to stage 13. |
| Analysis or robustness code | Rebuild stages 14–16 and any publication artifacts that use the changed results. |
| Article skeleton, manuscript text, or citation support | Create a new skeleton or manuscript version and repeat stages 17–20 as applicable. |

Do not narrow an invalidation because rerunning is expensive. If the effect is
uncertain, treat it as potentially material and ask the researcher.

## 8. Deviations and amendments

Log a deviation as soon as work departs from an approved, frozen, or
preregistered artifact. The deviation record identifies the run, affected
versions, discovery time, description, cause, effect assessment, action taken,
and researcher disposition.

A deviation is material if it changes—or could reasonably change—the research
question, population, hypotheses, estimand, measurement/codebook, unit space,
sampling, exclusions, data authorization, model route, validation, analysis, or
reported interpretation. Borderline materiality is a researcher decision.

- **Material:** stop affected work, set `waiting_for_user` or
  `awaiting_approval`, invalidate dependencies, and obtain the required amendment
  or redesign approval before resuming.
- **Nonmaterial:** still append the deviation and rationale, identify affected
  outputs, and continue only if the current stage permits it.
- **Discovered late:** preserve already produced work, mark it affected, and
  route back. Never rewrite history to make the deviation appear planned.

An external preregistration action cannot be fabricated. Archive the final
preregistration document locally, but record an external timestamp or identifier
only after the researcher actually completes or confirms that action.

## 9. Audits, corrections, and exact counts

- An audit produces a versioned findings artifact; it does not alter the audited
  artifact. Correction occurs in the named failure-route stage and creates a new
  version linked to the finding.
- Raw observations, human codes, adjudications, exclusions, and corrections
  remain distinct. A corrected row points to the superseded row rather than
  replacing it.
- Every run reports integers for attempted, succeeded, failed, unusable, and
  outstanding units, with definitions and denominators. Reconcile categories and
  explain any difference between corpus, eligible, attempted, analyzed, and
  reported counts.
- “No finding” and “not processed” are different values. Typed gap and unusable
  rows remain in manifests and denominator accounting.

## 10. Replication and retention

State schema 1.4 adds optional `run_checkpoint`: null, or an inline object with
`path` and `sha256` naming an immutable, payload-free local checkpoint. Old state
files remain valid. Verify it on resume; a `running` state cannot point to a
paused/stopped checkpoint. The checkpoint records evidence, not permission to
dispatch. Follow `operational-recovery.md` for reconciliation and migration.

Stage 16 must package or reference every active artifact needed to reproduce each
reported number: frozen prompts, raw outputs where sharing is authorized,
manifests, schemas, code, environment lock, decisions/deviations, and one rebuild
command. Restricted material receives a truthful access procedure or synthetic
test fixture, never a silently incomplete substitute.

The package is complete only after a fresh agent or process follows its README,
runs the rebuild from declared inputs, and verifies outputs against recorded
hashes or exact expected values. Record failures and route them to the originating
stage; do not patch the package by hand.
