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
prior line of research it extends (from the accepted preemption review, with
its version).

## Theory and hypotheses

TODO-PREREG each hypothesis with its stable ID from `hypotheses_vNNN.md`:
theory, variables, population, comparison, direction or explicitly
nondirectional test, decision rule, and primary/secondary/falsification/
exploratory label. Quote the exact hypotheses-file version and the value used to
verify that the file has not changed.

## Target population, frame, units, and denominator

TODO-PREREG target population, sampling frame, document unit, coding unit,
analysis unit, inclusion and exclusion rules, and the complete list or fixed
count of documents or other units eligible for coding. Quote the exact number
of eligible units and the value used to verify that the list has not changed.

## Corpus sources and authorization limits

TODO-PREREG each source, access route, coverage, and the authorization record
version with its limits on model exposure and redistribution.

## Sampling and partitions

TODO-PREREG the sample partitions (feasibility-probe units, prompt-development
examples, pilot units, held-out validation units kept separate from development,
and study units), the exclusions
that keep them independent, and the exact held-out validation seed or
fixed starting value for reproducing the sample selection (the random seed), or
other rule fixed at Stage 04 for selecting that sample in a way that could not be
changed after seeing results (for example, applying SHA-256, a standard method
for calculating a value that can verify that a file has not changed, to the
recorded list of frozen files).

## Power or precision analysis

TODO-PREREG the minimum detectable effect or target precision for each primary
estimand (the quantity the analysis seeks to estimate) at the approved power
and significance level, with the base-rate and sequential-screening assumptions
behind them and a pointer to the preserved formula or script.

## Variables, codebook, and schema

TODO-PREREG the exact codebook, required output format, and coding-prompt
versions and the values used to verify that those files have not changed, with
a one-line summary of each substantive variable and its evidence requirement.

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

TODO-PREREG the rule that each LLM conversation receives only one coding unit,
the retry policy, standard labels and reasons for failed assignments, quote
verification, and required-output checks.

## Held-out human validation

TODO-PREREG the held-out sample design, inclusion probabilities,
blinding and adjudication procedure, the double-coded reliability subsample
(or the recorded justification for a single-coder design), per-class and
subgroup metrics, and the acceptance thresholds chosen before results.

## Estimands, inference, and frozen analysis code

TODO-PREREG each quantity to be estimated, using its stable estimand ID, and its
inference procedure (how standard errors are calculated, the clustering level,
small-sample correction, confidence level, and whether the test is one- or
two-sided). Give the path and the value used to verify the frozen analysis
script that implements it under `project/code/frozen_analysis_vNNN/`, including
any listed parameters not yet fixed and the rule for fixing each without seeing
outcomes.

## Measurement-error correction and sensitivity analyses

TODO-PREREG the prespecified correction per estimand (see
`workflow/shared/measurement-error-correction-guide.md`), the validation
quantities it consumes, and the planned sensitivity analyses.

## Missingness, multiplicity, robustness, attrition, and stopping rules

TODO-PREREG the missing-data rules; the policy for correcting for multiple tests
(the multiplicity policy), with family
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
