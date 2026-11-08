---
title: "TODO-DRAFT: Short, concrete title"
authors: "TODO-DRAFT: Author names, or delete this line to print [Author Name]"
author_note: "TODO-DRAFT: Author information and acknowledgments, or delete this line"
running_title: "TODO-DRAFT: Short running head"
target_venue: "TODO-DRAFT: student-edited law review"
word_template: "law_review_v1"
sources: "project/runs/TODO-DRAFT/article_sources.csv"
values: "project/runs/TODO-DRAFT/article_values.csv"
source_versions: "TODO-DRAFT: project/artifacts/file_vNNN.ext; project/artifacts/other_vNNN.ext"
---

<!--
Illustrative law review article draft. Instructions: workflow/utilities/draft-article.md.
Voice, structure, footnotes, and framing: workflow/guides/law-review-article-style.md.
The builder (scripts/build_article_draft.py) refuses to run until every TODO-DRAFT is
replaced. It ignores comments like this one; delete them or leave them.

Conventions
  [^label]                      footnote marker; define it with  [^label]: text  anywhere
  {{src:ID}}                    in a footnote: the source-register row the citation rests on
  {{value:key}}                 a number from the values table (a pending row prints a placeholder)
  {{part:anchor}}               "Part II.A", "Appendix B", "Introduction"; anchor a heading with {#anchor}
  {{display:ID}}                "Table 2", "Figure 1", "Equation (3)"
  {{fn:label}}                  a footnote's number, as in  *supra* note {{fn:label}}
  [[citation needed: claim]]    an assertion that needs an authority not yet retrieved
  [[pending: what goes here]]   prose that waits on evidence still to come
  [[note: question]]            a Word comment for the researcher
  !display table|project/path#ID|caption        (figure adds |alt text; equation captions define terms)
  !pending figure|ID|caption                    a numbered display still to come
  *italic*  **bold**  [Small Caps]{.sc}  and  > block quotation (fifty words or more)

Optional metadata: abstract_word_limit (default 250) and draft_label (the sentence in the
author footnote that marks the draft as illustrative).
-->

# Abstract

<!-- 150-250 words, no footnotes: the question, what the study did in one plain sentence,
the headline finding, and why a lawyer should care. -->

TODO-DRAFT: Abstract, using {{value:key}} for every number and [[pending: ...]] for results still to come.

# Introduction {#intro}

<!-- Hook from the records; the question and stakes; what the study did; what it found,
most interesting finding first; two or three contributions; roadmap. -->

TODO-DRAFT: Hook paragraph: a case, puzzle, or piece of conventional wisdom the study tests.[^intro-hook]

TODO-DRAFT: The question and why it matters for law.

TODO-DRAFT: What the study did, in plain words, and what it found, leading with the most interesting result ({{value:key}}).

TODO-DRAFT: Two or three contributions, each measured against the closest prior work.[^intro-literature]

TODO-DRAFT: Roadmap. {{part:background}} explains ... {{part:design}} describes ... {{part:results}} reports ... {{part:implications}} considers ... {{part:app-data}} and the appendices after it hold the technical details.

[^intro-hook]: TODO-DRAFT: Full citation with a pinpoint {{src:ID}}.

[^intro-literature]: TODO-DRAFT: *See, e.g.*, full citation (parenthetical explaining the connection) {{src:ID}}; [[citation needed: the claim still needing an authority]].

# TODO-DRAFT: Background Part Title {#background}

<!-- The doctrine or debate, explained for a reader new to it; what earlier work found; the gap. -->

## TODO-DRAFT: The Doctrine {#background-doctrine}

TODO-DRAFT: Paragraphs, each opening with its point.

## TODO-DRAFT: What We Know and What We Don't {#background-gap}

TODO-DRAFT: Paragraphs.

# TODO-DRAFT: Design Part Title {#design}

<!-- Data, how the coding worked in ordinary terms, how it was checked; details to the appendix. -->

## Data {#design-data}

TODO-DRAFT: Paragraphs, with the details in {{part:app-data}}.

## How the Coding Worked {#design-coding}

TODO-DRAFT: Paragraphs.

## Checking the Coding {#design-validation}

TODO-DRAFT: Paragraphs.

# TODO-DRAFT: Results Part Title {#results}

<!-- Findings in order of interest, each tied to a display; null and fragile results in place. -->

TODO-DRAFT: Paragraphs. {{display:T1}} shows ...

!display table|project/artifacts/TODO-DRAFT.csv#T1|TODO-DRAFT: Caption that makes the table readable on its own.
!pending figure|F1|TODO-DRAFT: Caption for a figure still to come.

# TODO-DRAFT: Implications Part Title {#implications}

## TODO-DRAFT: What This Means for Doctrine {#implications-doctrine}

TODO-DRAFT: Paragraphs.

## Objections and Limits {#implications-limits}

TODO-DRAFT: Paragraphs.

# Conclusion

TODO-DRAFT: Short. Return to the hook; restate the contribution; nothing new.

# Appendix A. Data and Sample {#app-data}

TODO-DRAFT: Data construction and sample counts.

# Appendix B. Coding Instrument and Validation {#app-coding}

TODO-DRAFT: Codebook, prompt, and validation statistics.

# Appendix C. Estimation and Robustness {#app-robustness}

TODO-DRAFT: Estimating equations, robustness results, and additional tables.
