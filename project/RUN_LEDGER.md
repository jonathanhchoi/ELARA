# Run ledger

Append-only event log for every planning handoff that is recorded and every
execution attempt. Never replace a started event with a finished event; append a
new event for the same run ID. Corrections append a new event with `supersedes`.

## Event format

Append one block per event at the end of this file:

```text
## RUNEVT-YYYYMMDDTHHMMSSZ-NNN

- event_at: <UTC ISO 8601>
- event: <started | checkpoint | completed | failed | interrupted | superseded>
- run_id: <unique run ID>
- stage_id: <canonical stage ID>
- interaction_profile: <normal | plan | execute | plan_then_execute>
- code_or_prompt_version: <paths plus hashes>
- input_versions: <paths plus hashes>
- model_environment: <provider/model/version/parameters and environment lock or snapshot>
- attempted: <integer>
- succeeded: <integer>
- failed: <integer>
- unusable: <integer>
- outstanding: <integer>
- declared_outputs: <exact versioned paths or []>
- verification: <checks and results>
- error_or_stop_reason: <text or none>
- supersedes: <event ID or null>
- notes: <text or none>
```

For a closed execution run, `attempted` must reconcile with `succeeded + failed +
unusable`; report `outstanding` separately. Define and reconcile any additional
denominators such as corpus, eligible, processed, analyzed, and reported. A
failed, unusable, or interrupted run remains in the ledger.

Plan phases make no file changes. A normal-mode router may append a handoff event
before Plan Mode begins, but Plan Mode itself must leave this file untouched.

<!-- APPEND NEW RUN EVENTS BELOW THIS LINE. DO NOT EDIT PRIOR EVENTS. -->
