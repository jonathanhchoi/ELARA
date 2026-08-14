# Deterministic public-domain end-to-end fixture

This fixture is a tiny, no-network test of the executable core of the empirical legal
research workflow. It uses eight short clauses from the United States Constitution, a
public-domain United States government work. The source URLs are provenance strings only;
`rebuild.py` never retrieves them.

The recorded model rows are synthetic fixture outputs, not fresh model calls and not legal
interpretations. The binary field asks only whether the recorded coding instrument treats the
quoted text as assigning a role to a named federal institution. One deliberately incorrect
fixture row makes validation and measurement-error correction nontrivial. A paraphrase/second-
model fixture changes that row so robustness statistics are also nontrivial.

Run from this directory with only the Python standard library:

```text
python rebuild.py --output build
```

The rebuild performs the stage-08 pilot, stage-10 corpus integrity and provenance checks,
stage-11 scale-up plus strict schema and exact-quote verification, stage-12 support audit,
stage-13 human-code ingestion and validation metrics, stage-14 deterministic analysis and
measurement correction, stage-15 robustness comparison, and stage-16 replication packaging.
It fails closed if any source, schema, quote, identifier, denominator, or expected result does
not reconcile. The generated replication package can rebuild the same report in a new directory.

Authoritative source: National Archives, *The Constitution of the United States: A
Transcription*, <https://www.archives.gov/founding-docs/constitution-transcript>.

This fixture cannot substitute for a live novelty review, authorization decision, human gate,
external preregistration, or publishable validation study.
