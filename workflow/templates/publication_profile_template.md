# Publication profile template

Copy this file to `project/PUBLICATION_PROFILE_v001.md`, fill it in, and record
that file as the version currently in use in `project/PROJECT_STATE.md`, under
the literal state field `active_artifacts` with the label `publication_profile`.
To change it later, save a new version (`_v002`, ...) and record the new file as
the version in use; never edit a version that a manuscript run has already
recorded. Stages 18 and 20 and the
manuscript utilities (`elr-proofread`, `elr-add-citations`, `elr-apply-markup`)
read the current profile and record its exact version and a value used to verify
that the file has not changed. If no profile is current, those stages ask the
researcher to supply one or to record a decision to proceed by matching only the
existing draft's voice.

**Scope.** This profile governs prose, tone, formatting, and deliverable format
only. It cannot relax any guardrail, gate, evidence rule, or audit separation in
`workflow/shared/guardrails.md` or `workflow/shared/manuscript-editing-contract.md`.

**Precedence when instructions conflict.** (1) guardrails and the
manuscript-editing contract; (2) the researcher's task-specific instruction for
this run; (3) this profile; (4) the voice demonstrated by the existing draft;
(5) the kit's generic default (match the draft, change as little as possible).

Delete the guidance in brackets when you fill in a section. Leave a section as
`none` rather than deleting it, so a reader can see that it was considered.

## Venue and audience

- Venue: [journal or outlet, or "not yet chosen"]
- Peer reviewed: [yes / no / unknown]
- Primary audience: [for example "law students," "law professors interested in
  empirical legal research," "general scientific readers"]
- Venue format and length constraints to check: [none, or a URL and the limits]
- Word template: [law_review_v1 / journal_of_legal_analysis_v1 / supplied outlet template / none]
- Official formatting authority: [current official URL, or none]
- Official requirements checked: [YYYY-MM-DD, or none]
- Approved template fallback: [none, or the exact fallback and the researcher's approval]

For a peer-reviewed outlet other than the Journal of Legal Analysis, check the
outlet's current official requirements and use its supplied template when one
exists. Never silently substitute the JLA template. Record any fallback here
only after the researcher expressly approves it.

## Register and tone

- Descriptors: [for example "concise, interesting, and accessible"; "informal
  and helpful"; "concise, interesting, but highly rigorous"]
- Do not be florid or verbose; do not exaggerate. [keep, edit, or delete]
- Exemplar authors, if any: [names, and what to borrow from each — for example
  "the light, playful style of X; the adroit framing of Y"]

## Voice

- Match the existing authorial voice of the draft: [yes / no]
- If yes: carefully analyze and replicate the existing voice, tone, and writing
  style. Match sentence structure, vocabulary, level of formality, and rhetorical
  approach.
- Exemplar files (own prior work) under `project/inputs/manuscript/exemplars/`:
  [paths, or none]

## Minimal-change rule

- Where the draft already makes a point, change that writing as little as
  possible; change only what the approved task requires. [keep, edit, or delete]

## Prohibited constructions and punctuation

- Prohibited constructions: [for example: "That matters."; "That's not X; it's
  Y."; "X, and the X Ys."; end-of-sentence flourishes that add no content such
  as "and it's doing real work."]
- Punctuation preferences: [for example: no sentence contains more than one of a
  dash, a colon, and a semicolon; no paragraph uses a dash, colon, or semicolon
  in more than half of its sentences]
- Word and grammar preferences: [for example: "but" rather than "yet"; avoid the
  passive voice]

## Structure and placement

- Main findings: [for example "in the body, in language a reader with no social
  science background can follow"]
- Technical detail (model specifications, robustness checks, statistical tests):
  [for example "in the appendix"]
- Canonical language that must be reproduced exactly (statutory text, canons,
  defined labels): [where it lives, or none]

## Citations and names

- Citation style: [Bluebook / journal style / other]
- Author-reference conventions: [for example: first and last name at first
  mention, last name thereafter; "Judge X" or "Justice X" every time]
- Any citation practice the draft already follows that must be preserved: [notes]

## Required QA and deliverables

- Compile or render after editing: [yes / no] and inspect: [every page
  individually / the build log and rendered output]
- Review passes: [number]; each pass checks: [for example (1) instructions
  followed and numbers traced to results, (2) versioned draft compared with the
  source and the approved plan]
- Deliverable(s): [change log naming every edit and every requested edit not
  made; latexdiff or other redline; both]
- Researcher-note conventions in the draft: [for example: instructions in
  `[[double square brackets]]`; `[PENDING]` / `[DONE]` status flags in a
  comments file]
- Proofreaders' marks legend, if hand markup will be supplied: [legend, or none]

## Anything else

- [Other standing preferences for this manuscript, or none]
