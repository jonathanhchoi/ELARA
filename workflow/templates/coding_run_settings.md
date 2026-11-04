# Run settings for `scripts/coding_run.py`

Stages 08, 11, 12, and 15 run through one kit-owned runner. The project
supplies a settings file and a list of units; it does not write a driver. The
runner builds what each worker sees, prepares and seals the run with
`scripts/unit_fanout.py`, checks every return, applies the frozen retry rule,
writes the stage's dataset, ledger, and check files, and produces the review
sheet and agreement tables. Launching stays with the host's saved workflow or
sub-agents.

Save the settings as a versioned artifact: `coding_run_settings_vNNN.json`
(Stages 08 and 11), `audit_settings_vNNN.json` (Stage 12), or
`robustness_settings_vNNN.json` (Stage 15), all in `project/artifacts/`. Paths
inside it are relative to the settings file. The settings file the pilot accepts is the coding instrument
for Stage 11: Stage 11 reuses it unchanged with the full unit list, and the
run records its hash. Project code the runner does not cover (a corpus parser,
analysis) lives in one folder named by `project_code`; each run records that
folder's Git commit and a hash of its files instead of copying scripts.

## Commands

```text
python scripts/coding_run.py sample  --settings S --units UNITS.csv --out project/artifacts/pilot_sample_v001.csv
python scripts/coding_run.py prepare --settings S --units UNITS --run-dir project/runs/<run_id> [--dry-run]
python scripts/coding_run.py check   --run-dir project/runs/<run_id> [--apply] [--skip-retry ID] [--decided-by researcher]
python scripts/coding_run.py close   --run-dir project/runs/<run_id> [--version NNN]
python scripts/coding_run.py review  --run-dir project/runs/<run_id> [--version NNN] [--human-codes H.csv] [--blind]
python scripts/coding_run.py compare --run-dir project/runs/<run_id> [--version NNN] [--human-codes H.csv]
```

Every command prints JSON. `prepare` and `check` end with `next`, which is
exactly one of:

- `launch`: run the saved workflow with the arguments shown (`claude_code`), or
  on Codex list the block's assignments with the `discover` command and spawn
  `elr_worker` for each (`codex`);
- `check_apply`: run `check --apply` to apply the retry rule, record each
  failure decision in `failure_decisions.jsonl`, and write a checkpoint under
  `checks/`;
- `stop`: the stopping rule is met; stop launching and report the reasons;
- `close`: every unit is final; run `close`.

Repeat `launch` and `check --apply` until `next` says `close`. Any command can
be run again after an interruption; it reads only the run's files. `check`
shows operational counts only. `review` and `compare` show coded values and
refuse to run before `close`.

## What the run directory holds

`run_settings.json` (the exact settings), `run_spec.json` (everything
prepared, with hashes), `sources/` (line-numbered text or excerpts the workers
saw), `assignments/` (the exact instructions for each worker), `worker_returns/`
(the raw returns, never edited), `failure_decisions.jsonl`, `checks/`,
`close_receipt.json`, and the files `close` writes for the stage:

| Stage | `close` writes |
| --- | --- |
| 08 | `normalized_outputs.jsonl`, `pilot_ledger.csv`, `schema_quote_compliance.csv`, `quote_checks.csv` in the run directory |
| 11 | `coding_dataset_vNNN.jsonl`, `coding_ledger_vNNN.csv`, `schema_validation_vNNN.csv`, `quote_verification_vNNN.csv` in `project/artifacts/` |
| 12 | `interpretive_audit_vNNN.jsonl`, `interpretive_audit_coverage_vNNN.csv`, `interpretive_recoding_queue_vNNN.csv` in `project/artifacts/`; ledger and checks in the run directory |
| 15 | `robustness_dataset_vNNN.jsonl` in `project/artifacts/`; ledger and checks in the run directory |

`review` writes `pilot_researcher_review_vNNN.csv` for Stage 08 (otherwise
`researcher_review.csv` in the run directory). `compare` writes
`pilot_disagreements_vNNN.csv` for Stage 08 and `robustness_metrics_vNNN.json`
for Stage 15, plus `agreement.json` or `condition_disagreements.csv` and
`disagreeing_units.csv` (the unit-list rows where model codings disagree, ready
to be the unit list of a follow-on adjudication run). Nothing is overwritten;
an existing output stops the command.

## Settings fields

Required: `settings_version` (`"1.0"`), `stage`, and `inputs`. Optional
`description` is a free-text note.

- `inputs`: the frozen files, each `{"role", "path"}` with an optional
  `sha256` that must match. One role must be `result_schema`, the JSON Schema
  every result must pass. Express conditional requirements (a quote is
  required when a value is positive, a field is required for some categories)
  in that schema with `if`/`then`, `dependentRequired`, or `oneOf`.
- `read`: the roles each worker reads, in order (default: every input except
  replacement prompts).
- `units` (Stages 08, 11, 15): `id_column` (default `unit_id`); `fields`, the
  unit-list columns copied into each assignment; `sources`, each
  `{"source_id", "path_column", "root", "sha256_column"}` (a unit may have
  several documents); `max_chars`. A unit whose source is missing, not UTF-8,
  over `max_chars`, or lacks its window target is recorded as `unreadable` with
  the reason and stays in every count. A source whose recorded SHA-256 differs
  stops `prepare`.
- `view`: what workers see. `mode` is `full` (the file as is), `lines` (each
  line labeled `L1: `, `L2: `, ...; quotes cite `L12` or `L12-L14`), or
  `window` (`words_before` and `words_after` around a target found by
  `target_start_column`/`target_end_column` character offsets or
  `target_pattern`, marked with `marker_before` and `marker_after`, default
  `>>> ` and ` <<<`).
- `conditions`: default one condition, `base`. Each has an `id`,
  `replicates` (independent codings of every unit, default 1), optional
  `model` and `effort` (passed to the launch), and `replace`, which substitutes
  one input role for another for that condition (a prompt paraphrase:
  `{"instructions": "paraphrase_1"}`).
- `batch_size`: units per batch; each condition's units are split into
  numbered blocks and launched one block at a time.
- `time_box_minutes`: per worker (default 10).
- `quotes`: `anchors` lists where quotations sit in a result, by a simple path
  such as `exact_quote` or `observations[].evidence[]`. An anchor that points
  at objects names `quote_field` (default `quote`), `source_field`,
  `locator_field` (default `locator`), or `start_field`/`end_field`. Rules:
  `normalize` (`exact`; `whitespace`, which collapses runs of whitespace;
  `alphanumeric`, which compares lowercase letters and digits only and rejoins
  words hyphenated across lines), `case_sensitive` (default true),
  `fold_quotes` (curly to straight quotation marks), `whole_words`, `locator`
  (`none`, `line`, `offset`), `line_tolerance` (lines either side),
  `wrong_location` (`fail` by default, or `pass` when a quote found elsewhere
  in the unit is acceptable), `min_words`, `max_words`, and
  `unchecked_sources` (source labels, such as web pages, not held locally).
  Each anchor gets a status: `ok`, `ok_elsewhere`, `unchecked`, `empty`,
  `too_short`, `too_long`, `unknown_source`, `bad_locator`, `wrong_location`,
  or `not_found`.
- `retry`: `on`, the outcomes that get the one linked retry (`schema_failed`,
  `quote_failed`, `worker_error`, `refused`, `unreadable`, `wrong_document`),
  and `max_attempts` (1 or 2). A failure not retried is final.
- `stop`: the run-level stopping rule fixed with the pilot:
  `batch_failure_rate` and `cumulative_failure_rate` (share of units in
  completed blocks whose final outcome is a failure) and
  `consecutive_same_failure` (the same failure on that many attempts in a row).
- `sample`: `salt` and either `size` (allocated across `strata` in proportion,
  largest remainder) or `per_stratum`; `exclude` (lists of IDs to leave out,
  such as earlier pilots or the held-out validation sample), `require`
  (allowed values per column), `one_per` (at most one unit per value of a
  column, such as a docket), `min_chars`/`max_chars`. Units are ranked by the
  SHA-256 of `salt|unit_id`, so the draw is the same on every computer.
- `review`: `columns` the researcher fills in (defaults: valid yes/no,
  problem kind, reason, adjudicator), `blind_seed` for `--blind` (rows are
  shuffled, conditions become letters, and the key is written separately), and
  `human_id_column`.
- `compare`: `fields` (plain dotted paths into the result), `human_codes`,
  `human_id_column`, `human_coder_column`, `human_columns` (field to column),
  `reference` (the condition the others are compared with), and `bootstrap`
  (`seed`, `resamples`; resamples units for an interval on each paired
  difference in accuracy against the human codes). Pairwise output gives the
  number of shared units, raw agreement, Cohen's kappa (or why it is
  undefined), and the full cross-table.
- `audit` (Stage 12): the unit list is the Stage 11 coding dataset.
  `observations` is the path to observation objects inside each result (omit
  it to audit each coded result as one observation), `observation_id_field`,
  and `show_fields` or `hide_fields` to keep the coder's own reasoning or
  confidence away from the verifier. Use
  `workflow/templates/interpretive_audit_result.schema.json` as the
  `result_schema` input.
- `project_code`: the project's code folder, recorded by Git commit and file
  hash.

## Example (Stage 08 pilot)

```json
{
  "settings_version": "1.0",
  "stage": "08-pilot",
  "inputs": [
    {"role": "instructions", "path": "coding_prompt_v001.md"},
    {"role": "codebook", "path": "codebook_v001.md"},
    {"role": "result_schema", "path": "coding_schema_v001.json"}
  ],
  "units": {
    "id_column": "unit_id",
    "fields": ["court", "year"],
    "sources": [{"source_id": "opinion", "path_column": "text_path", "sha256_column": "text_sha256", "root": "../corpus/corpus_v001"}]
  },
  "view": {"mode": "lines"},
  "quotes": {
    "anchors": [{"path": "observations[].anchors[]", "source_field": "source_id"}],
    "normalize": "alphanumeric",
    "locator": "line",
    "line_tolerance": 1,
    "max_words": 30
  },
  "retry": {"on": ["schema_failed", "quote_failed", "worker_error"], "max_attempts": 2},
  "stop": {"batch_failure_rate": 0.05, "consecutive_same_failure": 5},
  "review": {"blind_seed": 20261104},
  "compare": {"fields": ["holding_type"], "human_codes": "pilot_human_codes_v001.csv"},
  "project_code": "../code"
}
```

## What the runner does not cover

Derived labels, majority or adjudication rules that combine codings, and
substantive analysis are research code under `project_code` (Stage 14) and
read the closed dataset. A step that needs a different unit list (a follow-on
adjudication run, a fresh sample after a contaminated pilot) is a new run with
its own settings or unit list. A coding route that calls a provider's API
directly, rather than through the host's workers, is outside this runner. If a
pilot needs something the runner cannot express, record it in the pilot's
revision queue and the kit issue report under
`workflow/shared/operational-recovery.md`; do not write a replacement driver.
