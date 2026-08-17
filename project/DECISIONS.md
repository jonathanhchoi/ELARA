# Decision log

Append-only record of researcher decisions, gate dispositions, external actions,
and approved exceptions. Never edit or delete an existing record. If a record is
wrong, append a correction with `supersedes` pointing to its ID.

A record with `decision: assistant-default` is a provisional choice the assistant
made to keep working between gates (see `workflow/shared/guardrails.md` section
11): `decision_text` states the choice, its one-line rationale, and the
alternatives. The next gate presents every provisional record since the last
gate; the researcher's gate decision names the IDs it keeps, and a changed one is
superseded by a new researcher record.

## Record format

Append one block per decision at the end of this file:

```text
## DEC-YYYYMMDDTHHMMSSZ-NNN

- decided_at: <UTC ISO 8601>
- stage_id: <canonical stage ID>
- run_id: <run ID or null>
- gate_id: <gate ID or null>
- decision: <approved | conditionally-approved | rejected | selected | amended | assistant-default | other>
- researcher_identity: <label supplied by researcher; do not infer; null for an assistant-default>
- decision_text: <verbatim or faithful decision text>
- artifact_pins: <repository-relative paths plus SHA-256 hashes, or []>
- conditions: <text or none>
- supersedes: <decision ID or null>
- recorded_by: <platform/agent label>
```

Gate approvals are ineffective unless the matching version-pinned record is also
represented in `PROJECT_STATE.md`. External preregistration or authorization is
recorded only after the researcher confirms the real action or identifier.

<!-- APPEND NEW DECISION RECORDS BELOW THIS LINE. DO NOT EDIT PRIOR RECORDS. -->
