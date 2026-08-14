# Measurement-error correction guide

This guide supports the researcher's Stage 04 correction decision and the Stage
03 inference gate, and Stage 14 consults it when checking that the approved
correction fits the data. It never authorizes Stage 14 to substitute a method:
if the approved correction is unsupported by the observed validation design,
Stage 14 stops and reports the incompatibility.

Read it under guardrails section 10. Sections 1, 3, and 4 are durable
requirements. Section 5 is a **dated menu** — a snapshot of the methods
literature as of this kit's release — and the methods literature for
LLM-assisted measurement is moving quickly. Do not treat the menu as the
answer; follow the protocol in section 2.

Contents:

1. Why a correction is mandatory
2. How to choose: a protocol, not a lookup
3. Requirements every correction imposes on the validation design
4. Failure modes to check before approval
5. A dated menu of corrections (verify currency before adopting)
6. References (dated leads)

## 1. Why a correction is mandatory

LLM labels are imperfect, and their errors are not random noise: models share
one direction of error across every document they touch, so confusion matrices
are typically imbalanced. Plugging raw LLM labels into an analysis biases
estimates and invalidates confidence intervals even when headline accuracy
exceeds 90 percent, and the bias can flip signs, not merely attenuate (Egami,
Hinck, Stewart & Wei 2023, NeurIPS; Ludwig, Mullainathan & Rambachan 2025, NBER
WP 33344; Choi & Connell 2024; Battaglia, Christensen, Hansen & Sacher 2025).
A validation sample plus a prespecified correction is therefore part of the
design, not an optional robustness check.

## 2. How to choose: a protocol, not a lookup

Reason from the problem, then research, then propose; the researcher decides.

1. **Characterize the estimand and design.** What quantity is being estimated
   (share, regression coefficient, index, something else)? Where does the
   LLM-coded variable enter (outcome, regressor, both)? What does the planned
   validation sample look like (probability design, expected per-class
   counts)?
2. **Research the current literature — by live retrieval, not from memory.**
   Search for current methods and software for valid inference with
   model-generated labels, using the section 6 references as entry points and
   following citations forward. Newer methods may dominate everything named in
   section 5; expect this.
3. **Shortlist candidate corrections** whose stated assumptions the planned
   validation design can actually satisfy (section 3), and check each
   candidate's failure modes against the design (section 4).
4. **Present the shortlist to the researcher** with the tradeoffs, the
   validation-design requirements each candidate imposes, and the retrieved
   sources — archived, with access dates, like any other source in this
   workflow. The researcher's choice, and its justification, go into the
   methods plan and the preregistration.

The durable rule is the shape of the solution, not any named estimator: a
small, honestly drawn gold-standard sample plus an explicit correction whose
assumptions are stated and whose first-stage uncertainty is propagated.

## 3. Requirements every correction imposes on the validation design

- The validation sample must be a probability sample of the study population —
  random, with **recorded inclusion probabilities**. A
  convenience sample supports no correction.
- Per-class counts must be large enough that the estimated
  error rates have usable precision; Stage 03 sizes the sample from
  confidence-interval half-width targets on exactly these quantities, and
  Stage 13 verifies the realized counts against those targets.
- The validation units must be coded by the **same model version, prompt, and
  configuration** as the production run. A provider version change breaks
  transportability (see the Stage 11 stop rule).
- First-stage uncertainty must be propagated: estimated sensitivity,
  specificity, or confusion structure is data, not a known constant.
- Human labels serving as ground truth need measured reliability: the
  double-coded subsample and chance-corrected agreement statistics of Stage 13.

## 4. Failure modes to check before approval

- **Sparse cells.** A rare class with two or three validated positives yields
  error-rate estimates too imprecise for any correction. Fix the design
  (enlarge the validation sample) at Stage 04, not the method at Stage 14.
- **Transportability.** Error rates that differ by era, court, or document
  quality make a pooled correction wrong; check and report error rates by
  subgroup where subgroup error is plausible.
- **Selection into validation.** If validation units were chosen because they
  looked hard, easy, or interesting, inclusion probabilities are unknown and
  the correction is unidentified.
- **Tuning leakage.** Any use of the held-out sample to select prompts, models,
  or thresholds invalidates it as a validation sample; the correction inherits
  the contamination.

## 5. A dated menu of corrections (verify currency before adopting)

The mapping below reflects the literature as of this kit's release (mid-2026).
Use it to orient the section 2 protocol's literature search — as candidate
methods and search terms — never as a closed menu. A newer method that
dominates one of these entries should be surfaced to the researcher with the
retrieved evidence.

| Estimand | Candidate correction (as of release) | Software (as of release) | Key assumptions |
|---|---|---|---|
| Prevalence or share of a binary label (for example, "share of opinions invoking a canon") | Misclassification-matrix correction (Rogan & Gladen 1978): invert estimated sensitivity and specificity; bootstrap the validation sample jointly with the corrected estimate so first-stage uncertainty propagates | Short scripted formula; bootstrap by hand or any stats package | Sensitivity and specificity estimated on a probability sample of the same population, same model version, adequate validated positives per class |
| Regression coefficient with an LLM-coded outcome or regressor | Design-based supervised learning (Egami et al. 2023) or prediction-powered inference (Angelopoulos, Bates, Fannjiang, Jordan & Zrnic 2023, Science); the two-regression recipe of Ludwig, Mullainathan & Rambachan 2025 is a simple defensible default for linear specifications | `dsl` (R), `ppi_py` (Python) | Gold-standard subsample drawn as a probability sample with recorded inclusion probabilities; expert labels treated as ground truth |
| Binary mismeasured regressor in a linear model | Aigner rescaling from estimated misclassification rates (Aigner 1973); note that error in a binary variable is never classical, attenuates OLS, and can inflate instrumental-variable estimates | Scripted formula; `validation_correction` (Python, Choi & Connell) | Misclassification rates constant across the covariate cells used, or estimated per cell |
| Continuous mismeasured covariate (for example, a model-scored intensity) | Regression calibration: replace the mismeasured covariate with its calibrated conditional expectation given validation data (Carroll, Ruppert, Stefanski & Crainiceanu 2006) | Standard implementations in R/Stata | Validation subsample measures the truth; calibration model correctly specified |
| Document-level labels aggregated into judge-, court-, or era-level indices | Joint estimation of the measurement model and the substantive model (Battaglia et al. 2025), which handles the index-error compounding that simple rescaling misses | `ValidMLInference` | Validation informative for the error process at the aggregation level actually used |
| Severe error, sparse classes, or nonstandard likelihoods | Full joint modeling per Battaglia et al. 2025 (Hamiltonian Monte Carlo), or redesign the measurement so the estimand is answerable | `ValidMLInference` | Researcher-approved model of the error process; enough validation data to identify it |

When in doubt between candidates, prefer the one whose assumptions the planned
validation design actually satisfies, and record the choice with its
justification in the methods plan.

## 6. References (dated leads)

These are entry points for the section 2 literature search, current as of the
kit's release; follow their citations forward.

- Aigner, D. J. (1973), "Regression with a Binary Independent Variable Subject
  to Errors of Observation," *Journal of Econometrics* 1(1): 49–59.
- Angelopoulos, A. N., S. Bates, C. Fannjiang, M. I. Jordan & T. Zrnic (2023),
  "Prediction-Powered Inference," *Science* 382: 669–674. Software: `ppi_py`.
- Battaglia, L., T. Christensen, S. Hansen & S. Sacher (2025), "Inference for
  Regression with Variables Generated by AI or Machine Learning." Software:
  `ValidMLInference`.
- Carroll, R. J., D. Ruppert, L. A. Stefanski & C. M. Crainiceanu (2006),
  *Measurement Error in Nonlinear Models: A Modern Perspective* (2d ed.).
- Choi, J. H. & P. Connell (2024), "Estimating and Correcting for Measurement
  Error in Machine-Coded Legal Data." Software: `validation_correction`.
- Egami, N., M. Hinck, B. M. Stewart & H. Wei (2023), "Using Imperfect
  Surrogates for Downstream Inference: Design-based Supervised Learning for
  Social Science Applications of Large Language Models," *NeurIPS 36*.
  Software: `dsl` (R).
- Ludwig, J., S. Mullainathan & A. Rambachan (2025), "Large Language Models: An
  Applied Econometric Framework," NBER Working Paper 33344.
- Rogan, W. J. & B. Gladen (1978), "Estimating Prevalence from the Results of a
  Screening Test," *American Journal of Epidemiology* 107(1): 71–76.
