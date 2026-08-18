# Deviation log

Append-only record of departures from approved, frozen, or preregistered
artifacts. Log a deviation when discovered, before silently adapting the work.
Never edit or delete a prior record; append a correction or disposition that
links to it.

## Record format

Append one block per deviation or disposition at the end of this file:

```text
## DEV-YYYYMMDDTHHMMSSZ-NNN

- detected_at: <UTC ISO 8601>
- stage_id: <canonical stage ID>
- run_id: <run ID or null>
- classification: <material | nonmaterial | pending-researcher-decision>
- status: <open | awaiting-approval | amended | accepted | remediated | superseded>
- description: <what differed from the approved/frozen plan>
- cause: <known cause or unknown>
- affected_artifacts: <paths plus versions/hashes>
- affected_approvals: <gate IDs or []>
- potential_effect: <scope, measurement, inference, authorization, or reporting effect>
- immediate_action: <pause, quarantine, route, or permitted continuation>
- failure_route: <canonical stage ID or null>
- decision_id: <linked researcher decision or null>
- amendment_identifier: <external/local amendment ID or null>
- supersedes: <deviation record ID or null>
```

The model must not down-classify a borderline deviation to keep a run moving.
Materiality and amendment disposition belong to the researcher. Late discovery
does not erase already produced artifacts; mark them affected and route back.

<!-- APPEND NEW DEVIATION RECORDS BELOW THIS LINE. DO NOT EDIT PRIOR RECORDS. -->
