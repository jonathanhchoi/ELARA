# Fresh-review protocol

Several stages end by handing their work to a "fresh reviewer" (Stages 01, 02,
05, 08, 10, 12, 14, 15, 18, and the fan-out contract). This file fixes what that
means, so the stages can name what is reviewed without restating how.

## Who reviews

- A fresh model context (a new subagent or a new session) that has not seen the
  drafting context, the intermediate reasoning, or the conclusion being tested.
  Where the platform allows and authorization and cost permit, prefer a
  different model family from the one that produced the work; disclose when
  the same family is used.
- The reviewer has no stake in the conclusion. Its prompt states that the goal
  is to find errors and to challenge the verdict, and that reporting "no
  problems found" requires the same evidence as reporting a problem.

## What the reviewer receives

- Only the artifact under review, the frozen instructions or definitions that
  govern it, and a deterministic route to the underlying sources (files,
  URLs, hashes). Never the author's confidence, a summary of why the answer is
  right, prior reviewer findings, or outcome information the stage keeps blind.

## What the reviewer does

- Reopens the sources: reruns or reperforms the checks the stage names, reopens
  every cited URL or file it is asked to reopen, and samples archived copies
  and hashes.
- Samples supports as well as flags: reviews items marked correct, verified, or
  supported, not only items already flagged, so agreement is tested and not
  assumed.
- Challenges the verdict: states what evidence would change it and looks for
  that evidence.
- Reports; it does not fix. The reviewer writes findings with the artifact and
  version, the location, the evidence, the severity, and the responsible
  correction route. It does not edit the artifact, recode an observation,
  repair code, or move an item from unverified to verified.

## What the stage does with the review

- Preserves the review and every disagreement between reviewer and author in
  the run directory or the stage report, including disagreements the stage
  resolves against the reviewer and why.
- Corrects factual errors only through the stage's normal versioned route.
  Failures of verification move to unverified; they are not argued back to
  verified without new evidence.
- Records in the run manifest who reviewed (model, route, settings when
  observable), what was sampled, and where the findings live.
