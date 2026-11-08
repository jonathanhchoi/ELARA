# Law review article style guide

The `elr-draft-article` utility (`workflow/utilities/draft-article.md`) writes an
illustrative draft of a law review article from the project's records, for the
researcher to rewrite. This guide sets the default voice, structure, footnote
practice, and framing for that draft.

The active publication profile (`project/PUBLICATION_PROFILE_vNNN.md`) overrides
this guide wherever it speaks. Neither the guide nor the profile can relax
`workflow/shared/guardrails.md` or `workflow/shared/manuscript-editing-contract.md`:
the draft cites only sources that were retrieved and read, takes every number
from the project's results, and invents nothing.

## 1. The requirements, as the researcher stated them

Writing style:

- This is a law review article intended for law students, so write in a
  concise, interesting, and accessible manner.
- Do not use jargon, but rather explain concepts clearly as necessary for an
  intelligent law student to understand them.
- Do not be florid or verbose; do not exaggerate. Think of the light, playful
  writing style of someone like Jonathan Choi.
- Ensure smooth transitions as updates are made. Ensure that the writing is
  consistent throughout the paper.

Structure:

- The paper includes an abstract, an introduction, Bluebook-style footnotes, and
  an appendix that contains additional technical details.
- The draft shows what a good version of the article might look like so that
  the researcher can iterate on it; a human rewrites it before submission. It
  may hold placeholders for empirical evidence still to come, but it should
  frame any known results in the way most interesting to law review editors.

## 2. What that voice looks like on the page

Do not rely on recognizing a named author's style. Aim for these concrete
features, and calibrate them against any of the researcher's own papers under
`project/inputs/manuscript/exemplars/`.

- **Plain words, short sentences.** Prefer the everyday word ("use," "show,"
  "about") to the formal one ("utilize," "demonstrate," "approximately"). Most
  sentences carry one idea. Vary length, but a sentence past forty words
  usually wants splitting.
- **The point first.** Each paragraph opens with a sentence that states its
  point; the rest of the paragraph supports it. A reader who skims the first
  sentences should still follow the argument.
- **Concrete before abstract.** Introduce an idea with a case, a hypothetical,
  a number, or a familiar comparison, then generalize. "Picture a judge with a
  dictionary open on the bench" beats "Judicial reliance on lexicographic
  sources has attracted scholarly attention."
- **Light, not jokey.** An occasional wry aside, a vivid example, or a
  deadpan understatement keeps the reader awake. The humor comes from the
  material, never from mocking a person or a court, and it never replaces an
  argument. A page or two between asides is about right.
- **Confident but calibrated.** Say plainly what the evidence shows and how
  sure we can be. Match the claim to the design: descriptive findings describe,
  associations associate, and only an identified causal design supports causal
  language. Never write "groundbreaking," "unprecedented," "crucial," or
  "dramatically."
- **Explain, don't name-drop.** Define every technical term at first use in a
  phrase a second-year law student can follow, or replace it with the plain
  description. Spell out an acronym the first time, as in "large language
  models (LLMs)." ELARA's own vocabulary never appears in the draft.
- **First person, used consistently.** "This Article argues" and "we find" are
  both fine; pick "I" or "we" to match the author list and keep it.

Plain-language equivalents that usually work in the body (keep the technical
term in the appendix, defined):

| Technical term | In the body |
|---|---|
| estimand | the quantity the study sets out to measure |
| inter-rater reliability, agreement statistic | how often two coders reach the same answer |
| confidence interval | the range of values consistent with the data (give the interval in a footnote or table) |
| statistically significant | unlikely to be a fluke of this sample, with the test in a footnote |
| measurement error correction | an adjustment for the mistakes the automated coding makes, based on how often it disagreed with careful human coders |
| robustness check | rerunning the analysis a different reasonable way to see whether the answer changes |
| preregistration | a public, dated plan of the analysis written before seeing the results |

Habits to avoid, because readers recognize them as filler: "It is important to
note that"; "delve"; "landscape"; "tapestry"; "underscores"; "not X, but Y"
flourishes; ending paragraphs with an aphorism; lists of three adjectives;
sentences that stack a dash, a colon, and a semicolon. The builder flags the
common ones as warnings.

## 3. Architecture of the article

Adapt the architecture to the project. A heavily doctrinal question needs a
longer background Part; a methods-forward article needs a longer design Part.
The builder requires an Abstract, an Introduction, at least two numbered Parts,
a Conclusion, and at least one Appendix.

- **Title.** Short and concrete; a question or a claim works well. A subtitle
  after a colon can carry the technical description.
- **Abstract** (150–250 words, no footnotes). The question, what the study did
  in one plain sentence, the headline finding, and why a lawyer, judge, or
  legislator should care. When a result is pending, keep its sentence as a
  placeholder rather than guessing.
- **Introduction** (about a tenth of the text, footnoted generously). Open with
  a hook drawn from the records: a case, a puzzle, or a piece of conventional
  wisdom the study tests. Then the question and why it matters; what the study
  did, in plain words; what it found, leading with the finding most likely to
  interest editors; two or three concrete contributions measured against the
  literature in the preemption review; and a roadmap paragraph that names each
  Part with `{{part:...}}` cross-references.
- **Background Part.** The doctrine or debate, explained for a reader who has
  not taken the relevant upper-level course; what earlier work established; the
  gap this study fills.
- **Design Part.** The data, how the coding worked, and how it was checked. For
  model-assisted coding, say in ordinary terms what the model was asked to do,
  what it returned, and how its answers were compared with careful human
  coding. Point to the Appendix for prompts, codebook, and statistics.
- **Results Part.** Findings in order of interest, each tied to a table or
  figure, each number read in plain language ("about two in five opinions").
  Report null, mixed, and fragile results honestly in the relevant place, not
  in a footnote. Summarize robustness checks and send the details to the
  Appendix.
- **Implications Part.** What the findings mean for doctrine, practice, and
  theory, followed by a candid subpart on objections and limits.
- **Conclusion.** Short. Return to the hook, restate the contribution, and add
  nothing new.
- **Appendix.** The technical detail: data construction and sample counts, the
  codebook and prompt, validation statistics, estimating equations, robustness
  results, and additional tables. The appendix may be more technical than the
  body, but it still defines its terms.

## 4. Framing results for law review editors

Student editors read hundreds of submissions and decide mostly from the title,
abstract, and the first pages. Frame known results so those pages answer three
questions: what is surprising, why it matters for law, and why the reader
should believe it.

- Lead with a puzzle, a widely held assumption the data tests, or a decisive
  answer to a live doctrinal debate. A finding that cuts against conventional
  wisdom is the strongest lead; a careful confirmation of something people only
  assumed is the next strongest.
- State the doctrinal or practical payoff: what a court, lawyer, agency, or
  legislature might do differently because of the finding.
- Give magnitudes in words a lawyer feels ("about 40 percent," "one opinion in
  ten") and put intervals and test statistics in a footnote, table, or the
  Appendix.
- Present a null result as informative when the design can rule out effects
  that would matter ("if there is an effect, it is small").
- Treat the method as the means, not the headline, unless the article is about
  the method. "We read 12,000 opinions" interests editors more than the model's
  name.
- Do not overclaim. Editors and peer readers punish a causal claim the design
  cannot support far more than a modest, well-supported one.
- For a result still to come, write the surrounding paragraph so it reads
  sensibly whichever way the result turns out, put a `[[pending: ...]]`
  placeholder saying exactly what goes there, and record in the drafting memo
  how the framing would change under each plausible outcome.

## 5. Footnotes and Bluebook practice

Law review readers expect a footnote for every factual, legal, or empirical
assertion in the text that is not common knowledge, and for every quotation.
Footnotes also carry caveats, technical asides, and cross-references.

- **Typeface (law review footnotes).** Signals, *Id.*, *supra*, *infra*, and
  explanatory phrases are italicized. Case names are roman in full citations and
  italicized in short forms and in textual sentences. Article titles are
  italicized; book titles and authors and periodical names are in large and
  small caps (write `[Harv. L. Rev.]{.sc}`).
- **Signals.** No signal when the source directly states the proposition;
  *See* when it supports it by inference; *See also*, *Cf.*, *Compare ...
  with ...*, *But see*, and *See generally* as the Bluebook defines them. Add an
  explanatory parenthetical whenever the connection is not obvious.
- **Pinpoints.** Give a pinpoint page or section for every quotation and every
  specific proposition.
- **Short forms.** Give the full citation the first time a source appears. Use
  *Id.* only for the single authority cited in the immediately preceding
  citation; the builder checks this. Use "Author, *supra* note N" for secondary
  sources (never for cases, statutes, or constitutions, which take their own
  short forms); write it as `*supra* note {{fn:label}}` so the number follows
  the footnotes when they move, and the builder checks that note N cites the
  same source.
- **Quotations** of fifty words or more go in a block quotation (`> `), with the
  footnote after the quotation.
- **Numbers.** Follow Bluebook rule 6.2 in text and footnotes; in practice the
  body says "42 percent" rather than "42%."
- **Sources.** Every citation carries `{{src:ID}}` naming a row of the run's
  source register, which points to the archived copy that was read. Where an
  assertion needs an authority the project has not retrieved, write
  `[[citation needed: the exact claim]]` instead of a citation; `elr-add-citations`
  fills those later. Never complete a citation from memory, and never cite a
  source for more than it says.
- When a Bluebook form is uncertain, keep the citation complete and accurate and
  add `[[note: check Bluebook form]]` in the paragraph rather than guessing.

## 6. Consistency and transitions, in every version

- State the thesis the same way in the Abstract, the Introduction, and the
  Conclusion.
- Open each Part with a sentence that connects it to the Part before and says
  what this Part does; close it by setting up the next.
- Write every number with `{{value:key}}`, using one key for one quantity
  everywhere, and every cross-reference with `{{part:...}}`, `{{display:...}}`,
  or `{{fn:...}}`, so numbers and references cannot drift apart.
- Define each term once and use the same term throughout; keep the glossary in
  the drafting memo.
- Use the present tense for what the Article argues and finds ("we find"), the
  past tense for what the study did ("we coded"), and one tense consistently for
  prior work.
- After any revision, reread the whole draft, not only the changed passages.
  Check every paragraph and Part boundary next to a change, and update the
  Abstract, Introduction, roadmap, and Conclusion whenever a finding, a Part, or
  the order of Parts changed.

## 7. Placeholders

- `{{value:key}}` with a `pending` row in the values table prints
  `[[pending: description]]`; the number appears once the row is verified.
- `[[pending: ...]]` marks prose that depends on evidence still to come. Say
  what goes there ("one sentence on whether the effect persists after 2010"),
  not just "TBD."
- `!pending table|ID|caption` (or `figure`, `equation`) reserves a numbered
  display; refer to it as `{{display:ID}}`.
- `[[citation needed: claim]]` marks an assertion that needs an authority.
- `[[note: ...]]` becomes a Word comment. Use it only for what the researcher
  must decide or notice, such as a framing choice or a claim that depends on
  their judgment.

All visible placeholders are highlighted in the Word draft and listed, with
their locations, in the run manifest and the drafting memo.
