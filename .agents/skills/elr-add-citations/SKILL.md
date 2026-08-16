---
name: "elr-add-citations"
description: "Research, retrieve, and add only the citations the researcher marked as needed, in the publication profile's citation style, then route the new manuscript version through the audit-only Stage 18. Use when the researcher asks to add or supply citations for specific passages."
---

# Run elr-add-citations

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`,
   `workflow/shared/artifact-contract.md`, and `workflow/shared/manuscript-editing-contract.md` completely,
   then the active publication profile pinned in `project/PROJECT_STATE.md`
   (`project/PUBLICATION_PROFILE_vNNN.md`), if any.
2. Read `workflow/utilities/add-citations.md` completely and follow it as the single source of
   substantive instructions for this utility.
3. This is an optional manuscript utility, not a pipeline stage: never change `current_stage`,
   and append the run ledger and decisions only as the canonical file directs.
4. Honor the utility's phases. Do not edit any manuscript file before the researcher grants
   the permission the canonical file names; a skill cannot switch Plan or Goal mode by itself.
5. Afterwards follow the route the canonical file names (`workflow/stages/18-cite-check.md`) rather than
   treating the utility's output as final.
