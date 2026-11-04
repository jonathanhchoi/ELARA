# Fresh-review protocol

Several stages hand their work to a "fresh reviewer" (Stages 01, 02, 05, 08,
10, 12, 14, 15, 18, and the fan-out contract). This file fixes what that means.

- **Who:** a fresh model context (a new sub-agent or session) that has not seen
  the drafting context, the intermediate reasoning, or the conclusion under
  test. Prefer a different model family where the platform, authorization, and
  cost allow; disclose when the same family is used. Its prompt says the goal is
  to find errors and challenge the verdict, and that "no problems found" needs
  the same evidence as a problem.
- **What it receives:** only the artifact, the frozen instructions or
  definitions that govern it, and a deterministic route to the sources (files,
  URLs, hashes). Never the author's confidence, a case for the answer, earlier
  reviewers' findings, or outcomes the stage keeps blind.
- **What it does:** reopens the sources and reruns the checks the stage names;
  samples items marked correct or supported, not only flagged ones; states what
  evidence would change the verdict and looks for it; and reports findings
  (artifact and version, location, evidence, severity, correction route). It
  never edits the artifact, recodes, repairs code, or moves an item to verified.

## How many reviews

- A stage run gets exactly the fresh reviews its stage file names, once each. A
  later run of the stage (a re-pilot, a recoding run) gets its own.
- A finding is fixed through the stage's normal versioned route, and the fix is
  confirmed by re-running the check that failed (a validator, `coding_run.py
  check`, `stage_check.py`), never by another review. Do not review a review,
  review a fix, review operational or setup work, or repeat a review because
  something changed.
- A further review of the same work happens only when the researcher asks for
  one. A fatal or major finding the stage cannot fix in place follows the
  stage's failure route.

## What the stage does with it

Keep the review and every disagreement with it (including those resolved
against the reviewer, and why) with the run. A failed verification returns to
verified only with new evidence. Record who reviewed (model, route, settings),
what was sampled, and where the findings are.
