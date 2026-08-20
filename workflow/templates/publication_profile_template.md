# Publication profile template

Copy this file to `project/PUBLICATION_PROFILE_v001.md`, fill it in, and pin it
in `project/PROJECT_STATE.md` under `active_artifacts` as `publication_profile`.
To change it later, save a new version (`_v002`, ...) and repin; never edit a
version that a manuscript run has already recorded. Stages 18 and 20 and the
manuscript utilities (`elr-proofread`, `elr-add-citations`, `elr-apply-markup`)
read the active profile and record its version and SHA-256 hash in their run
manifests. If no profile is active, those stages ask the researcher to supply one
or to record a decision to proceed by matching the existing draft's voice only.

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
