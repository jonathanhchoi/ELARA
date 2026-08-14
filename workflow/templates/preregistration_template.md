# Preregistration

Instantiate this template at Stage 09 (`workflow/stages/09-freeze-and-preregister.md`).
Complete every section; replace every `TODO-PREREG` marker. The Stage 09
verification step greps for unresolved `TODO-PREREG` markers, so an incomplete
draft fails mechanically. State registered facts without reporting or
forecasting study outcomes: the registration freezes tests and decision rules,
not results.

## Title and authorship

TODO-PREREG title, authors, affiliations, and contact.

## Research question and contribution

TODO-PREREG the one-sentence question, the claimed contribution, and the
lineage it extends (from the accepted preemption review, with its version).

## Theory and hypotheses

TODO-PREREG each hypothesis with its stable ID from `hypotheses_vNNN.md`:
theory, variables, population, comparison, direction or explicitly
nondirectional test, decision rule, and primary/secondary/falsification/
exploratory label. Quote the active hypotheses artifact version and hash.

## Target population, frame, units, and denominator

TODO-PREREG target population, sampling frame, document unit, coding unit,
analysis unit, inclusion and exclusion rules, and the closed unit-space
denominator. Quote the unit-space row count and SHA-256 hash exactly.

## Corpus sources and authorization limits

TODO-PREREG each source, access route, coverage, and the authorization record
version with its limits on model exposure and redistribution.

## Sampling and partitions

TODO-PREREG the sample partitions (feasibility-probe units, prompt-development
examples, pilot units, held-out validation units, study units), the exclusions
that keep them independent, and the exact held-out validation seed or
non-gameable derivation rule (for example, SHA-256 of the frozen-artifact
manifest) fixed at Stage 04.

## Power or precision analysis

TODO-PREREG the minimum detectable effect or target precision for each primary
estimand at the approved power and significance level, with the base-rate and
funnel assumptions behind them and a pointer to the archived formula or script.

## Variables, codebook, and schema

TODO-PREREG the codebook, schema, and coding-prompt versions and hashes, with a
one-line summary of each substantive variable and its evidence requirement.

## Model and prompt route

TODO-PREREG the model or agent route, exact model identifier, configuration
including provider defaults, and the reproducibility limits of hosted models
(what a replicator can and cannot rerun).

## Pilot procedure and disclosures

TODO-PREREG the pilot design, everything learned from it, every design change
it prompted, and every pilot unit seen. Disclose that pilot-informed choices
are not untouched priors. Confirm the pilot reported measurement quality only
and no substantive estimand was computed.

## Coding procedure and mechanical checks

TODO-PREREG one-unit-per-context coding, retry policy, typed failure statuses,
quote verification, and schema validation rules.

## Held-out human validation

TODO-PREREG the held-out sample design, inclusion probabilities,
blinding and adjudication procedure, the double-coded reliability subsample
(or the recorded justification for a single-coder design), per-class and
subgroup metrics, and the acceptance thresholds chosen before results.

## Estimands, inference, and frozen analysis code

TODO-PREREG each estimand with its stable ID and its inference procedure
(standard-error estimator, clustering level, small-sample correction,
confidence level, sidedness), and the path and SHA-256 of the frozen analysis
script that implements it under `project/code/frozen_analysis_vNNN/`, including
any enumerated open parameters and the outcome-blind rule for each.

## Measurement-error correction and sensitivity analyses

TODO-PREREG the prespecified correction per estimand (see
`workflow/shared/measurement-error-correction-guide.md`), the validation
quantities it consumes, and the planned sensitivity analyses.

## Missingness, multiplicity, robustness, attrition, and stopping rules

TODO-PREREG the missing-data rules; the multiplicity policy with family
definitions by hypothesis ID and the exact correction procedure (or the
researcher's recorded justification for none); the robustness conditions
(prompt paraphrases, second model) and their materiality criterion; the corpus
gap-rate threshold and prespecified attrition treatment; and the stopping
rules.

## Confirmatory versus exploratory boundary

TODO-PREREG which analyses are confirmatory and fully specified here, and the
rule under which later analyses are labeled exploratory.

## Deviations and amendments

TODO-PREREG the amendment policy version and how deviations will be logged,
classified as material or nonmaterial, and reported.
