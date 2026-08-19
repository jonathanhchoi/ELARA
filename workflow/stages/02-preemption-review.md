---
stage_id: "02-preemption-review"
title: "Run the selected-project preemption review"
paper_steps: ["1"]
core: true
interaction_profile: "execute"
long_running: true
goal_condition: "Run Stage 02 exactly as specified until the exhaustive search ledger reconciles, every relied-on source is retrieved and verified, all declared artifacts pass validation, and PROJECT_STATE.md records the preemption-disposition gate, or until an ELARA section 11 stop condition is recorded and surfaced; do not decide the gate for the researcher."
prerequisites: ["00-initialize"]
required_inputs: ["project/PROJECT_STATE.md", "project/PROJECT_CHARTER_vNNN.md", "selected project decision", "project/artifacts/conception_report_vNNN.md or researcher-supplied project memorandum"]
declared_outputs: ["project/artifacts/preemption_review_vNNN.docx", "project/sources/preemption/<run_id>/source_manifest.csv", "project/sources/preemption/<run_id>/search_log.csv", "project/sources/preemption/<run_id>/claim_evidence.csv", "project/sources/preemption/<run_id>/retrieved/", "project/sources/preemption/<run_id>/fanout/<wave>/ (query matrix, spec.json, briefs, sealed manifest, launch record, worker returns, merged candidates)", "project/runs/<run_id>/preemption_review_source.md", "project/runs/<run_id>/rendered_preemption_review/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
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
5. Confirm that `python scripts/build_preemption_review.py --help` succeeds and that the host can render DOCX files to page images for visual inspection. A missing renderer is an environment gap, not permission to activate an uninspected document.

## Researcher decisions

The researcher decides:

- whether a partially preempted project should distinguish, extend, narrow, combine, or stop;
- whether inaccessible database results must be supplied before accepting the verdict;
- which doctrinal and disciplinary lineages define the claimed contribution; and
- whether the remaining contribution justifies a feasibility audit.

The agent may recommend a disposition but must not approve novelty or silently reshape the project.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. This is a long-running execution stage: its front-matter
`goal_condition` must be the active goal before execution begins. If it is not
active, provide `/goal <goal_condition>` and stop. Do not run the review in Plan
Mode. In Codex, run every search, author, citation-chain, and retrieval wave as
the kit's `elr_research_worker` sub-agents. In Claude Code, run those waves as
the saved `elr-research-fanout` workflow, which the assistant launches itself.
Both routes follow `workflow/shared/observation-fanout.md`; the stage goal stays
with the parent through wave validation and final reconciliation.

## Work

1. Allocate a unique run ID, record the active artifact versions and search question, and append a ledger start. Assume the project is preempted and try to prove it.
2. Before building the query matrix, run a bounded smoke screen — about thirty minutes, no query matrix, no hashing, no fresh review. Confirm from live sources that the proposed corpus exists at a named authoritative source, that a public sample or metadata page is reachable, and that no facial license or terms bar blocks the planned use. When Stage 01 was skipped, also apply the Stage 01 selection tests to the researcher-supplied project: the question is statable in one sentence, either plausible result is interesting, the task is estimation from supplied text rather than outcome prediction, the variables look verifiable from single documents, and execution is plausible in weeks rather than years. Record a one-page pass/fail note with the probe links in the run manifest and hand it to Stage 03 so the full data gate does not repeat these probes. A failed smoke screen stops with waiting_for_user or routes to 01-conceive before any exhaustive searching begins; it never silently reshapes the project.
3. Build a query matrix spanning the question, construct synonyms, unit, jurisdiction, period, corpus, method, claimed result, leading cases or statutes, and citation chains. Log every query verbatim, with route, timestamp, result count when available, and disposition.
4. Run at least fifteen genuinely distinct queries, broad before narrow, across at least four suitable routes: scholarly search or OpenAlex; law-school repositories and law-review sites; SSRN and working-paper title searches; relevant disciplinary indexes or repositories such as NBER, OSF, arXiv, SocArXiv, or institutional archives; and the open web for conference programs, symposia, calls, datasets, dissertations, and works in progress. Use available subscription databases only within the researcher's authorization. Run the queries, author searches, citation chains, retrievals, and the fresh review as research fan-outs under `workflow/shared/observation-fanout.md` ("Research fan-outs" and "Worker tool surface, time boxes, and crash-resume"): for each wave, write one brief per query, author, chain, or work and a `spec.json` under `project/sources/preemption/<run_id>/fanout/<wave>/`, seal it with `python scripts/research_fanout.py prepare`, and hand the directory to the host's orchestrator — in Claude Code the saved `elr-research-fanout` workflow, launched by the assistant; in Codex the kit's `elr_research_worker` sub-agents, spawned by name in bounded waves — never an all-tools agent, never one hand-launched worker at a time, never a serial imitation in the parent's context. The controller records launches, bounds attempts, and reports what is pending, so a wave interrupted by a crash resumes from the files; after each wave the parent validates the returns, merges them into the search log and candidate list, and appends a ledger checkpoint. A worker that meets a 401/403/429, CAPTCHA, bot challenge, or login wall records a typed access gap and moves on. For every potentially material work whose full text remains blocked, the parent then runs the parent-only browser fallback in `workflow/shared/observation-fanout.md`: try lawful open routes first, then use browser control in the researcher's main authorized session for one bounded ordinary-UI retrieval attempt. The parent, never a worker, logs route `parent_browser_fallback`; unresolved sources feed the manual search packet in step 11.
5. Once close authors appear, search each author's publication page, CV, repository, coauthors, datasets, and related papers. Follow backward and forward citations and inspect relevant review articles. Rank by substantive proximity and importance, not title similarity.
6. Continue until three consecutive well-designed new queries yield no previously unseen close work. Record the saturation queries; do not stop merely because a preferred answer emerged. One early exit exists: if a retrieved and fully read work decisively occupies the same thesis, evidence, and contribution, the review may truncate — retrieve, hash, and fresh-review that work, complete the escape-route analysis for it, mark the review `truncated on decisive preemption`, and go straight to the preemption-disposition gate. A truncated record cannot support a later `open` verdict or a repositioned project without a full rerun.
7. Retrieve each work relied upon. Save lawful full-text copies under the run directory and hash them. For every item, record full citation, persistent and landing URLs, access date, publication status, venue, retrieval status, retrieval surface (including `parent_browser_fallback` where used), full-text-read status, local path, and whether it is verified or unverified. Validate a browser-downloaded file as the identified work rather than a challenge or error page before hashing and reading it. A snippet, abstract, another paper's citation, or model memory cannot make an item verified.
8. Create claim_evidence.csv linking every substantive description and preemption claim to the source ID, page or section, and a short supporting quotation. Stay within lawful quotation limits. If full text cannot be reached, label the attribution unverified and give the researcher the exact title, locator, database, and query needed.
9. Construct the annotated map of the closest works. For each, state its actual question, data, method, thesis, publication status, and precisely why it does or does not occupy the same contribution. Treat working papers, forthcoming articles, dissertations, active datasets, and legal developments that moot the question as live threats.
10. Render one verdict: preempted, partially preempted, or open. Before preempted, test distinguish, extend, new era or courts, new scale, new measurement, and limitations acknowledged by the prior authors. Before open, run and log a final skeptic search designed to disprove novelty. State discoveries that would flip the verdict and report no confidence score.
11. Report an honest contribution sentence, lineage, scoop risk, active researchers, inaccessible routes, exact manual search packet, check date, and recommended recheck date. Record the recheck date and the scoop-risk level in the preemption-disposition approval record's conditions so Stage 04 can check staleness mechanically.
12. Give the draft and evidence table to a fresh reviewer with no stake in the conclusion (per `workflow/shared/fresh-review.md`). The reviewer must reopen every cited URL, validate bibliographic identity and attributed claims, sample archived files and hashes, and challenge the verdict. Correct factual errors; move failures to unverified; preserve the review trail.
13. Instantiate `workflow/templates/preemption_review_template.md` as the run-scoped `project/runs/<run_id>/preemption_review_source.md`. Preserve the required section order and complete every metadata field. Build the new versioned Word artifact with `python scripts/build_preemption_review.py project/runs/<run_id>/preemption_review_source.md project/artifacts/preemption_review_vNNN.docx`. The Markdown file is an auditable build source, not the active researcher-facing report. Render the DOCX to page images under `project/runs/<run_id>/rendered_preemption_review/`, inspect every page at 100 percent zoom, and iterate on the source until headings, paragraphs, lists, tables, hyperlinks, page breaks, headers, and footers are clean. Never patch the generated DOCX by hand. If no DOCX renderer is available, record the gap, leave the artifact inactive, and set `waiting_for_user` with the exact rendering capability needed.

## Artifacts

preemption_review_vNNN.docx is the active, researcher-facing literature review. It must contain, in order, the annotated map, verdict and flip conditions, positioning and lineage, scoop risk, search methods and saturation evidence, access limitations and manual search packet, and review date. The run-scoped preemption_review_source.md is the exact build source and remains immutable when the run closes. The source manifest, query-level search log, claim-evidence table, retrieved copies, rendered page images, and run manifest are mandatory support artifacts. Do not cite a source absent from the manifest.

## Verification

- Confirm the smoke screen ran and its pass/fail note is in the run manifest, and that the minimum query, route, author-search, citation-chain, and saturation requirements hold from the search log — or, for a review truncated on decisive preemption, that the decisive work was retrieved, read, hashed, and fresh-reviewed and the truncation is stated prominently in the review artifact.
- Confirm that every potentially material 401/403/429, CAPTCHA, bot-challenge, login-wall, or automated-download gap was either resolved through a lawful open route, given one parent browser-control attempt recorded as `parent_browser_fallback`, or assigned a typed reason why browser retrieval was unavailable or unauthorized. Confirm that no worker received an interactive tool and that every unresolved item appears in the access limitations and manual search packet.
- Reopen every cited URL and confirm that every verified work was actually read and every substantive attribution has pinpoint evidence.
- Confirm that inaccessible sources remain unverified and that absence claims point to logged searches rather than intuition.
- Confirm that the verdict applies thesis-level preemption, includes escape routes and flip conditions, and distinguishes topic overlap from the same question and evidence.
- Confirm the fresh review is archived or summarized in the run manifest and all discrepancies are resolved or disclosed.
- Confirm the DOCX opens successfully, carries the required metadata and section hierarchy, contains no unresolved template marker, and was rendered after its last build. Inspect every rendered page for clipped or overlapping text, broken lists or tables, bad page breaks, missing glyphs, and inconsistent headers or footers. Record the render command, renderer version, page count, and inspection result in the run manifest.
- Confirm no previous artifact, ledger row, source, or input was overwritten.

## State transition

Set current_stage to 02-preemption-review and status to running only when execution begins. If retrieval fails before a defensible review is possible, set status to waiting_for_user, list the inaccessible sources or databases, append exact counts, and keep prior active artifacts unchanged.

After verification, activate the new review, set status to awaiting_approval, mark preemption-disposition pending, and request an explicit proceed, reposition, return to conception, or stop decision. On proceed, append the accepted verdict and contribution sentence to DECISIONS.md, mark the gate approved, and set current_stage to 03-feasibility-audit and status to ready. A material repositioning requires a versioned targeted rerun of this stage; a rejected or preempted project returns to 01-conceive or the researcher-supplied selection path.

## Next-stage handoff

Tell the researcher the verdict, remaining access gaps, active review version, and date when novelty should be rechecked. After explicit acceptance, provide the exact next task: run 03-feasibility-audit using the accepted question, contribution, corpus, variables, and closest-work map, and stop at the feasibility go/no-go gate.
