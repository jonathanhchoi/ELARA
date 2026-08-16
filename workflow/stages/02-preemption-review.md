---
stage_id: "02-preemption-review"
title: "Run the selected-project preemption review"
paper_steps: ["1"]
core: true
interaction_profile: "execute"
long_running: true
prerequisites: ["00-initialize"]
required_inputs: ["project/PROJECT_STATE.md", "project/PROJECT_CHARTER_vNNN.md", "selected project decision", "project/artifacts/conception_report_vNNN.md or researcher-supplied project memorandum"]
declared_outputs: ["project/artifacts/preemption_review_vNNN.md", "project/sources/preemption/<run_id>/source_manifest.csv", "project/sources/preemption/<run_id>/search_log.csv", "project/sources/preemption/<run_id>/claim_evidence.csv", "project/sources/preemption/<run_id>/retrieved/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "preemption-disposition"
next_stage: "03-feasibility-audit"
failure_routes: ["01-conceive", "02-preemption-review"]
---

## Objective

Conduct an exhaustive, adversarial, retrieved-source literature review of the selected project. Map the closest published and unpublished work, test thesis-level rather than topic-level novelty, identify viable escape routes, and give the researcher a verified preemption record and honest verdict.

## Prerequisite checks

1. Read AGENTS.md and PROJECT_STATE.md, then confirm an approved Stage 00 charter and an explicit selected-project decision. Stage 01 may be skipped only if that skip and the researcher-supplied project are recorded.
2. Restate the selected question, intended data, method, comparison, and claimed new contribution. If any element is indeterminate enough to change search results, obtain clarification before starting.
3. Load earlier conception sources only as leads. Reopen and independently verify them; an earlier citation or screen is not evidence for this stage.
4. Confirm current live web access. If key subscription databases are unavailable, the review may proceed only with a conspicuous access gap and an exact researcher search packet; it may not claim completeness.

## Researcher decisions

The researcher decides:

- whether a partially preempted project should distinguish, extend, narrow, combine, or stop;
- whether inaccessible database results must be supplied before accepting the verdict;
- which doctrinal and disciplinary lineages define the claimed contribution; and
- whether the remaining contribution justifies a feasibility audit.

The agent may recommend a disposition but must not approve novelty or silently reshape the project.

## Mode handoff

This is a long-running execution stage. Codex and current Claude Code may use /goal when available, with normal researcher-approved execution as the fallback. Use the objective: Execute the exhaustive Stage 02 preemption review for the selected project, verify every cited source, produce all declared artifacts, and stop at the preemption-disposition gate. If the user has not entered an execution mode, provide that handoff and stop. Do not do this review in Plan Mode.

## Work

1. Allocate a unique run ID, record the active artifact versions and search question, and append a ledger start. Assume the project is preempted and try to prove it.
2. Before building the query matrix, run a bounded smoke screen — about thirty minutes, no query matrix, no hashing, no fresh review. Confirm from live sources that the proposed corpus exists at a named authoritative source, that a public sample or metadata page is reachable, and that no facial license or terms bar blocks the planned use. When Stage 01 was skipped, also apply the Stage 01 selection tests to the researcher-supplied project: the question is statable in one sentence, either plausible result is interesting, the task is estimation from supplied text rather than outcome prediction, the variables look verifiable from single documents, and execution is plausible in weeks rather than years. Record a one-page pass/fail note with the probe links in the run manifest and hand it to Stage 03 so the full data gate does not repeat these probes. A failed smoke screen stops with waiting_for_user or routes to 01-conceive before any exhaustive searching begins; it never silently reshapes the project.
3. Build a query matrix spanning the question, construct synonyms, unit, jurisdiction, period, corpus, method, claimed result, leading cases or statutes, and citation chains. Log every query verbatim, with route, timestamp, result count when available, and disposition.
4. Run at least fifteen genuinely distinct queries, broad before narrow, across at least four suitable routes: scholarly search or OpenAlex; law-school repositories and law-review sites; SSRN and working-paper title searches; relevant disciplinary indexes or repositories such as NBER, OSF, arXiv, SocArXiv, or institutional archives; and the open web for conference programs, symposia, calls, datasets, dissertations, and works in progress. Use available subscription databases only within the researcher's authorization.
5. Once close authors appear, search each author's publication page, CV, repository, coauthors, datasets, and related papers. Follow backward and forward citations and inspect relevant review articles. Rank by substantive proximity and importance, not title similarity.
6. Continue until three consecutive well-designed new queries yield no previously unseen close work. Record the saturation queries; do not stop merely because a preferred answer emerged. One early exit exists: if a retrieved and fully read work decisively occupies the same thesis, evidence, and contribution, the review may truncate — retrieve, hash, and fresh-review that work, complete the escape-route analysis for it, mark the review `truncated on decisive preemption`, and go straight to the preemption-disposition gate. A truncated record cannot support a later `open` verdict or a repositioned project without a full rerun.
7. Retrieve each work relied upon. Save lawful full-text copies under the run directory and hash them. For every item, record full citation, persistent and landing URLs, access date, publication status, venue, retrieval status, full-text-read status, local path, and whether it is verified or unverified. A snippet, abstract, another paper's citation, or model memory cannot make an item verified.
8. Create claim_evidence.csv linking every substantive description and preemption claim to the source ID, page or section, and a short supporting quotation. Stay within lawful quotation limits. If full text cannot be reached, label the attribution unverified and give the researcher the exact title, locator, database, and query needed.
9. Construct the annotated map of the closest works. For each, state its actual question, data, method, thesis, publication status, and precisely why it does or does not occupy the same contribution. Treat working papers, forthcoming articles, dissertations, active datasets, and legal developments that moot the question as live threats.
10. Render one verdict: preempted, partially preempted, or open. Before preempted, test distinguish, extend, new era or courts, new scale, new measurement, and limitations acknowledged by the prior authors. Before open, run and log a final skeptic search designed to disprove novelty. State discoveries that would flip the verdict and report no confidence score.
11. Report an honest contribution sentence, lineage, scoop risk, active researchers, inaccessible routes, exact manual search packet, check date, and recommended recheck date. Record the recheck date and the scoop-risk level in the preemption-disposition approval record's conditions so Stage 04 can check staleness mechanically.
12. Give the draft and evidence table to a fresh reviewer with no stake in the conclusion (per `workflow/shared/fresh-review.md`). The reviewer must reopen every cited URL, validate bibliographic identity and attributed claims, sample archived files and hashes, and challenge the verdict. Correct factual errors; move failures to unverified; preserve the review trail.

## Artifacts

preemption_review_vNNN.md must contain, in order, the annotated map, verdict and flip conditions, positioning and lineage, scoop risk, search methods and saturation evidence, access limitations and manual search packet, and review date. The source manifest, query-level search log, claim-evidence table, retrieved copies, and run manifest are mandatory support artifacts. Do not cite a source absent from the manifest.

## Verification

- Confirm the smoke screen ran and its pass/fail note is in the run manifest, and that the minimum query, route, author-search, citation-chain, and saturation requirements hold from the search log — or, for a review truncated on decisive preemption, that the decisive work was retrieved, read, hashed, and fresh-reviewed and the truncation is stated prominently in the review artifact.
- Reopen every cited URL and confirm that every verified work was actually read and every substantive attribution has pinpoint evidence.
- Confirm that inaccessible sources remain unverified and that absence claims point to logged searches rather than intuition.
- Confirm that the verdict applies thesis-level preemption, includes escape routes and flip conditions, and distinguishes topic overlap from the same question and evidence.
- Confirm the fresh review is archived or summarized in the run manifest and all discrepancies are resolved or disclosed.
- Confirm no previous artifact, ledger row, source, or input was overwritten.

## State transition

Set current_stage to 02-preemption-review and status to running only when execution begins. If retrieval fails before a defensible review is possible, set status to waiting_for_user, list the inaccessible sources or databases, append exact counts, and keep prior active artifacts unchanged.

After verification, activate the new review, set status to awaiting_approval, mark preemption-disposition pending, and request an explicit proceed, reposition, return to conception, or stop decision. On proceed, append the accepted verdict and contribution sentence to DECISIONS.md, mark the gate approved, and set current_stage to 03-feasibility-audit and status to ready. A material repositioning requires a versioned targeted rerun of this stage; a rejected or preempted project returns to 01-conceive or the researcher-supplied selection path.

## Next-stage handoff

Tell the researcher the verdict, remaining access gaps, active review version, and date when novelty should be rechecked. After explicit acceptance, provide the exact next task: run 03-feasibility-audit using the accepted question, contribution, corpus, variables, and closest-work map, and stop at the feasibility go/no-go gate.
