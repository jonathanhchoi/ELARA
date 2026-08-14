---
stage_id: "18-cite-check"
title: "Audit every manuscript citation against retrieved sources"
paper_steps: ["6"]
core: false
interaction_profile: "execute"
long_running: true
prerequisites: ["17-integrate-manuscript"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/manuscript_vNNN/", "project/artifacts/manuscript_change_log_vNNN.md", "project/artifacts/manuscript_consistency_report_vNNN.md", "project/artifacts/replication_package_vNNN/", "researcher-supplied bibliography, source files, and authorized database access where applicable"]
declared_outputs: ["project/artifacts/citation_audit_vNNN.jsonl", "project/artifacts/citation_audit_report_vNNN.md", "project/sources/cite_check/<run_id>/source_manifest.csv", "project/sources/cite_check/<run_id>/search_log.csv", "project/sources/cite_check/<run_id>/retrieved/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: null
next_stage: "19-revise-and-respond"
failure_routes: ["17-integrate-manuscript", "18-cite-check"]
---

## Objective

Audit every source-dependent manuscript proposition and citation against the actual retrieved authority, including identity, text, pinpoint, version, and material authority concerns. Produce a complete finding report and source archive. This stage is audit-only: it must not edit the manuscript, bibliography, source files, or citation code.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Resolve the exact active manuscript and replication-package versions and record their hashes. Confirm the manuscript builds or renders and identify the actual main file, bibliography databases, footnotes or endnotes, citation commands, and generated sections.
2. Confirm lawful access routes for cases, statutes, regulations, articles, books, filings, archives, and subscription sources. If a source requires researcher access, prepare an exact retrieval request rather than substituting a summary or model memory.
3. Parse an inventory of every distinct cited source and every claim-citation pair, including citations in notes, captions, tables, appendices, quotations, parentheticals, and generated text. Preserve stable IDs so repeated citations can share a source but retain claim-specific findings.
4. Confirm the audit output can be written without modifying manuscript inputs. If a prerequisite fails, make no writes and leave state unchanged.

## Researcher decisions

The researcher decides which unavailable sources to supply, the governing citation style and authority standard, and how to respond later to unsupported, outdated, or strategically weak citations. The auditor may classify and explain findings. It may not repair citations, rewrite propositions, infer that a famous source probably supports a claim, or replace an inaccessible authority with a plausible substitute.

## Mode handoff

This is a long-running audit stage. In Codex or current Claude Code, `/goal` may be used with this objective: **Retrieve and read the actual source for every manuscript claim-citation pair, verify identity, proposition, quotation, pinpoint, version, and relevant authority status, archive the evidence, and report every problem without editing the manuscript.** If Goal mode is unavailable, use normal approved execution with durable checkpoints. Do not use Plan Mode for the audit.

## Work

1. Allocate a unique audit run ID and output versions, record manuscript and package hashes, set the stage running, and append a ledger start.
2. Build a source and claim inventory before judging any citation. For each claim-citation unit, record manuscript location, proposition, quoted language if any, citation string or key, source type, and retrieval need.
3. Retrieve the real source from an official reporter, court, legislature, agency, publisher, repository, DOI landing page, or other authoritative route. Archive a lawful copy when permitted and record full citation, stable and landing URLs, access date, local path, checksum, publication or decision status, version, and retrieval limitations.
4. Use one claim-citation pair per audit context. Read the source itself and enough surrounding material to understand the proposition. Search snippets, headnotes, citator summaries, abstracts, another author's footnote, and model memory are leads, not verification.
5. For a case, verify court, year, opinion or separate writing, quoted text, holding versus dicta or party argument, pinpoint, and any subsequent history material to the manuscript's claim. For a statute or regulation, verify jurisdiction, version and effective date, text, section, and amendments. For scholarship, verify bibliographic identity, page, actual claim, method, and whether the manuscript overstates it.
6. Assign each pair a documented disposition such as supported, supported with qualification, pinpoint or metadata error, source mismatch, quotation error, proposition unsupported, authority or version concern, or unverified because the actual source was unavailable. Include a concise explanation, pinpoint, and short supporting quotation where lawful.
7. Check internal citation integrity: missing bibliography entries, orphaned entries, duplicate or inconsistent keys, broken cross-references, citations attached to the wrong clause, citation-needed claims, quotation and source mismatches, and inconsistent short forms. Report only; do not fix.
8. Log every search and failed access attempt. If the source cannot be obtained, identify the exact document, database, route, and query the researcher should use. Never turn an unverified item into a verified one based on plausibility.
9. Have a fresh reviewer reopen every severe finding and a sample from each other disposition, validate source identity and supporting text, and challenge claims marked supported. Preserve reviewer disagreements and resolve only the audit classification, not the manuscript.
10. Reconcile the final audit to the inventory and create a prioritized report organized by manuscript location and problem type. State clearly that findings remain unfixed.

## Artifacts

`citation_audit_vNNN.jsonl` contains one immutable record per claim-citation pair with manuscript location, proposition, source ID, disposition, explanation, pinpoint, evidence, and review status. The source manifest records bibliographic identity, URLs, access dates, local paths, hashes, versions, restrictions, and verification status. The search log supports unavailable-source findings. Retrieved files contain only lawful copies. `citation_audit_report_vNNN.md` summarizes coverage, severe errors, qualifications, pinpoint and metadata issues, unverified items and exact retrieval requests, internal-integrity findings, and fresh-review results. No output is a revised manuscript.

## Verification

- Confirm every claim-citation pair in every manuscript component has exactly one audit record and inventory and disposition counts reconcile.
- Reopen each source used to mark a claim supported and confirm identity, version, pinpoint, quotation, context, and proposition from the actual document.
- Confirm case, statutory, regulatory, and scholarly checks include the source-type-specific authority and version questions relevant to the claim.
- Confirm unavailable sources remain unverified with complete search logs and exact researcher requests; no citation or quotation was supplied from memory.
- Confirm fresh review covers all severe findings and a documented sample of supports and qualifications, with disagreements disclosed.
- Diff or hash manuscript and bibliography inputs before and after the run and confirm the audit made no edits and overwrote no prior source or finding.

## State transition

Set `current_stage` to `18-cite-check` and `status` to `running` only after checks pass. If a source needed for a defensible finding is available only to the researcher, preserve completed audit work, set `status` to `waiting_for_user`, and record the exact requested file or access action. An unavailable source may receive an explicit unverified disposition if the researcher chooses to proceed with that limitation.

After every inventory unit has a verified or expressly unverified disposition and review passes, activate the audit, report, source manifest, logs, and run; set `current_stage` to `19-revise-and-respond`; and set `status` to `ready`. Findings remain findings until the researcher approves a revision plan; do not claim the citations were corrected.

## Next-stage handoff

Tell the researcher the total claim-citation pairs and sources, disposition counts, every severe error, qualifications, unavailable-source requests, authority concerns, and exact audit and manuscript versions. State that no manuscript file changed. Then provide the exact next task: plan `19-revise-and-respond`, map each audit finding and reviewer comment to a proposed disposition, and stop for manuscript-edit permission before changing prose, citations, or analysis code.
