---
title: "TODO-FEASIBILITY: Full Feasibility Analysis for the selected project"
subtitle: "TODO-FEASIBILITY: State the exact accepted research question"
recommendation: "TODO-FEASIBILITY: go, go with modifications, or no-go"
audit_date: "TODO-FEASIBILITY: YYYY-MM-DD"
consultation_date: "TODO-FEASIBILITY: YYYY-MM-DD"
consultation_record: "TODO-FEASIBILITY: project/runs/<run_id>/feasibility_consultation.md"
report_version: "TODO-FEASIBILITY: vNNN"
---

## Decision summary

> **Bottom line:** TODO-FEASIBILITY: State the recommended decision, the
> binding reason, and the practical consequence for the project.

TODO-FEASIBILITY: Summarize the least expensive check likely to show that the
project cannot work, the usable-data range, the minimum detectable effects (the
smallest effects the design is likely to distinguish from zero), the default
sub-agent completion-time range, the estimated cost of doing the same work
through the optional pay-per-token API route, and any decision that belongs to
the researcher. Identify the consultation record and state how the researcher's
answers changed the recommendation, assumptions, or proposed design.

## Is the coding task one that LLMs are good at?

**Decision:** TODO-FEASIBILITY: Pass, pass with conditions, or fail.

**Evidence:** TODO-FEASIBILITY: Cite the evidence IDs and explain whether each
proposed use determines a value from only the supplied text (estimation) or
infers something beyond that text (prediction).

**Analysis:** TODO-FEASIBILITY: Present the full reasoning, alternatives,
tradeoffs, and leakage analysis rather than only the disposition.

**What this means:** TODO-FEASIBILITY: Explain the practical consequence in
plain language, including any risk that the answer comes from material seen
during model training rather than from the documents supplied for the study.

**Researcher input:** TODO-FEASIBILITY: Cite the decision ID and summarize the
researcher's answer, or state that no researcher-owned choice arose in this section.

**Conditions or next step:** TODO-FEASIBILITY: State any required change or
write "None".

## Can a careful human verify each coding decision from the source?

**Decision:** TODO-FEASIBILITY: Pass, pass with conditions, or fail.

**Evidence:** TODO-FEASIBILITY: Cite the evidence IDs and describe the exact
quotation or other source-based verification method for every proposed variable.

**Analysis:** TODO-FEASIBILITY: Analyze each variable, the plausible
decompositions or replacements, likely disagreements, and the consequences of
each defensible choice.

**What this means:** TODO-FEASIBILITY: Explain likely disagreements and any
holistic, expert, novel, or cross-document judgment that cannot be checked reliably.

**Researcher input:** TODO-FEASIBILITY: Cite the decision ID for every construct
choice put to the researcher, quote or faithfully summarize the answer, and
identify anything the researcher left unresolved.

**Conditions or next step:** TODO-FEASIBILITY: State any required change or
write "None".

## Would this be an interesting contribution to the literature regardless of the direction of the results?

**Decision:** TODO-FEASIBILITY: Pass, pass with conditions, or fail.

**Evidence:** TODO-FEASIBILITY: Give the most defensible headline under each
result direction, identify the audience, and cite the closest-literature evidence.

**Analysis:** TODO-FEASIBILITY: Compare both result directions against the
closest literature and explain the substantive and publication tradeoffs.

**What this means:** TODO-FEASIBILITY: Explain whether both directions support
a contribution.

**Researcher input:** TODO-FEASIBILITY: Cite the decision ID and state the
researcher's view of the proposed contributions and audience.

**Conditions or next step:** TODO-FEASIBILITY: State any required repositioning
or write "None".

## Can we obtain and use the data the project needs?

**Decision:** TODO-FEASIBILITY: Pass, pass with conditions, or fail.

**Evidence:** TODO-FEASIBILITY: Cite IDs for current live checks of the source,
coverage, formats, descriptive fields, selection, gaps, identifiers, OCR,
access behavior, and terms.

**Analysis:** TODO-FEASIBILITY: Explain every tested access route, observed
limitation, coverage or selection tradeoff, and material failed probe.

**What this means:** TODO-FEASIBILITY: Explain whether an authorized sample
contains the information the project proposes to code.

**Researcher input:** TODO-FEASIBILITY: Cite the decision ID for accepted
coverage gaps, selection risks, or access alternatives, or state that no
researcher-owned choice arose in this section.

**Conditions or next step:** TODO-FEASIBILITY: State the access, license, or
data change required, or write "None".

## Will there be enough usable data to answer the research question?

**Decision:** TODO-FEASIBILITY: Pass, pass with conditions, or fail.

**Evidence:** TODO-FEASIBILITY: Cite the estimated frequency, low, central, and
high projections of how many records remain after each screening and coding
step, minimum detectable effects, assumptions, and preserved formula.

**Analysis:** TODO-FEASIBILITY: Walk through the complete observation funnel,
power calculations, plausible effect-size benchmarks, validation-precision
calculation, clustering or design effects, and sensitivity to each major assumption.

**What this means:** TODO-FEASIBILITY: Explain in plain language whether the
planned comparisons can detect an effect that would matter.

**Researcher input:** TODO-FEASIBILITY: Cite the decisions approving or changing
the target population and comparison, power and significance level, effect-size
benchmark, validation precision, and double-coding share; preserve unknowns.

**Conditions or next step:** TODO-FEASIBILITY: State any sample, scope, power,
or validation change required, or write "None".

## Can the project be completed in a reasonable amount of time with the available resources?

**Decision:** TODO-FEASIBILITY: Pass, pass with conditions, or fail.

**Evidence:** TODO-FEASIBILITY: Cite the timing check, the record of available
access and software, the timing-and-cost calculations, price sources, and
authorization evidence.

**Analysis:** TODO-FEASIBILITY: Show the full scenario calculations, bottlenecks,
serial steps, resource alternatives, and sensitivity to uncertain duration,
retry, token, staffing, or authorization assumptions.

**Sub-agent timing:** TODO-FEASIBILITY: Give low, central, and high elapsed
completion times from expected assignments, the recorded limit on simultaneous
sub-agents, per-assignment duration, retries, validation steps that must run one
at a time, and the time needed to combine results. Do not give the
subscription-backed route a dollar value.

**API-price comparison:** TODO-FEASIBILITY: Separately estimate what the same work
would cost through the optional API route, using current prices, projected
tokens, retries, model cost-and-capability levels, and available batch
discounts, with price-sheet URLs and access dates.

**Human and other resources:** TODO-FEASIBILITY: State validation and other
burdens as time or capacity, record known fixed charges, and flag spending decisions.

**What this means:** TODO-FEASIBILITY: Explain whether the schedule and known
resource constraints fit the researcher's stated limits.

**Researcher input:** TODO-FEASIBILITY: Cite decisions about the acceptable
timeline, available human capacity, fixed charges, and any nontrivial spending.

**Conditions or next step:** TODO-FEASIBILITY: State any timing, capacity,
authorization, or spending change required, or write "None".

## Could coding errors change the answer, and can the analysis account for them?

**Decision:** TODO-FEASIBILITY: Pass, pass with conditions, or fail.

**Evidence:** TODO-FEASIBILITY: Cite the variable-level error analysis,
validation quantities, and current support for the proposed correction or sensitivity analysis.

**Analysis:** TODO-FEASIBILITY: Trace each plausible error process to the
estimand, compare defensible correction or sensitivity approaches, and explain
what the validation data can and cannot identify.

**What this means:** TODO-FEASIBILITY: Explain how false positives, false
negatives, subgroup errors, missing documents, or refusals could change the answer.

**Researcher input:** TODO-FEASIBILITY: Cite decisions about acceptable error
risk, the preferred correction or sensitivity route, and any unresolved design choice.

**Conditions or next step:** TODO-FEASIBILITY: State the correction, audit, or
validation change required, or write "None".

## Does a legal, ethical, data-use, or spending issue require the researcher’s decision?

**Decision:** TODO-FEASIBILITY: Pass, pass with conditions, or fail.

**Evidence:** TODO-FEASIBILITY: Cite the relevant terms, licenses,
institutional rules, ethics materials, confidentiality constraints, and spending record.

**Analysis:** TODO-FEASIBILITY: Explain the issue, the available routes and
tradeoffs, what evidence is missing, and why the agent cannot decide it.

**Researcher decision needed:** TODO-FEASIBILITY: State each decision that
belongs to the researcher, or write "None".

**What this means:** TODO-FEASIBILITY: Explain why the issue can or cannot be
resolved without the researcher's express authorization.

**Researcher input:** TODO-FEASIBILITY: Cite each decision ID and quote or
faithfully summarize the answer, including "don't know" or deferral where given.

**Conditions or next step:** TODO-FEASIBILITY: State the exact approval or
information needed, or write "None".

## Researcher consultation and decisions

**Consultation status:** TODO-FEASIBILITY: Complete, or complete with unresolved choices.

**Decisions incorporated:** TODO-FEASIBILITY: List every consultation decision
ID, the concrete question asked in chat, the recommendation and alternatives
presented, the researcher's exact answer or a faithful quotation, and how the
answer changed or confirmed the analysis. Distinguish an accepted recommendation,
"don't know," and an unresolved issue. Do not convert silence or an earlier
general instruction into a decision.

TODO-FEASIBILITY: State whether any material researcher-owned choice remains
unresolved and where it appears as a condition in this report.

## Controlling limitation

TODO-FEASIBILITY: Name the single limitation that controls the recommendation,
identify the decisive evidence, and explain why it is controlling.

## Recommendation and what would change it

TODO-FEASIBILITY: Recommend go, go with modifications, or no-go. State exactly
what new evidence or project change would alter the recommendation. Report no
confidence score.

## Evidence gaps and limitations

TODO-FEASIBILITY: List every unverified assumption, failed or unavailable
probe, access limitation, unresolved factual dispute, and deferred authorization.
