# Restarting coding without changing the research

Read this with Stage 11 and `observation-fanout.md`. The host still launches
restricted workers; `unit_fanout.py` still validates, retries, and merges.
`scripts/fanout_lifecycle.py` is a provider-neutral journal, not a launcher,
scientific validator, source of retry permission, or replacement model route.

## Classify the interruption before acting

- **Unit failure:** apply the recorded `failure_handling` preference and frozen
  retry/stopping rules. Preserve the return and linked decision.
- **Infrastructure failure:** preserve the stop and process evidence, establish
  whether a worker launched, and inspect only authorized operational evidence.
  Under recorded authorization covering this class, diagnose, test, independently
  review, and version a repair without asking the same approval again.
- **Scientific change:** changes to instructions, source representation, model,
  route, isolation, accepted results, retry rules, or exclusions follow the
  existing amendment and approval gates. Calling a change operational is not proof.
- **Authorization gate:** ask once for the missing decision. A repeated heartbeat
  or stale `running` state supplies no decision.

No return means unknown finality unless affirmative evidence proves otherwise.
An unacknowledged launch intent may have reached the host. Never silently
relaunch that attempt, invent a no-judgment finding, fabricate a return, or
allocate a retry from absence alone. Explicit exceptions remain scoped to the
units and attempts the researcher approved.

## One stable implementation, durable evidence

Use one versioned runtime with explicit configuration and compatibility adapters.
Do not generate another recursively inherited wrapper, launch namespace, or
historical exception table for each recoverable incident. Preserve old code as
evidence, not as a requirement to recursively execute all old versions. If an
old run sealed implementation bytes, record and approve operational migration
before changing the entrypoint. Never weaken the old seal or discard history.

For a new or explicitly migrated run, the host adapter uses `Journal` as follows:

1. Initialize a bounded-segment journal with scientific and operational binding hashes,
   concurrency, and attempt limits. Record the exact adapter version separately.
2. Hold `ownership()` around dispatch. It persists PID plus creation identity
   and refuses another owner. Recover an abandoned owner only after independent
   process-tree/lock checks and recorded review; ambiguous identity fails closed.
   Journal ownership is not a substitute for host-tree checks.
3. Record `intent` before each host spawn and `acknowledged` after the host
   acknowledges it. Neither proves a judgment. Record `returned`, `validated`,
   and `reconciled` separately, each linked to its authoritative receipt hash.
   Only the frozen controller/validator determines these facts.
4. Record a linked retry only after the controller allocated it under frozen
   policy. The journal prevents duplicate unit-attempt dispatch within that segment, but a supplied
   receipt hash is a reference, not independently verified scientific evidence.
5. On interruption, reconcile existing returns before consulting controller
   pending assignments. Never reconstruct research progress from chat history.

Journal replay is deliberately complete before each mutation. Keep each journal
bounded to a small dispatch segment, not the full corpus: replay cost grows with
its history. The host adapter must maintain an authenticated segment index and
checkpoint lineage and prove every prior segment attempt terminal before opening
the next segment. Keep linked retries in their original segment until reconciled;
never move an unknown-finality or retryable attempt into a fresh journal. The
controller's pending list alone cannot detect an unreturned prior launch. Global
uniqueness and exactly-once dispatch across segments remain adapter obligations.
These segment boundaries limit bookkeeping work, not total units, tokens, time,
or the researcher's approved concurrency.

Store closed operational identifiers and categories only, never prompts, labels,
result bodies, exception strings, or model output. Existing raw material stays
in its authorized location. Existing controller formats remain unchanged.

Read-only commands:

```
python scripts/fanout_lifecycle.py inspect --directory <run>/batch_checks/lifecycle/<segment>
python scripts/fanout_lifecycle.py resume-plan --directory <run>/batch_checks/lifecycle/<segment>
```

After quiescence, use `checkpoint --directory <run>/batch_checks/lifecycle/<segment> --output
<run>/batch_checks/checkpoints/checkpoint_vNNN.json`. Record the snapshot path and SHA-256 as
`run_checkpoint` in project state. Old projects without this field remain valid.
A fresh session verifies that anchor, reconstructs current controller facts, and
resolves discrepancies before dispatch.

## Verify the failing boundary and report actual progress

A restart dry-run must exercise the operation that failed, not only the older
checks before it. It must not stage state, create retries, or start workers.
Test an interrupted wave and a fresh process using the real controller with a
synthetic host. A separate synthetic restricted-worker round-trip establishes
live capability; offline checks alone cannot establish model access.

`VerificationTransaction` reuses expensive proof computation in one process only
while every bound file still hashes identically. It rechecks bytes, not just
timestamps, and never persists a bypass or carries trust to another wave. Apply
it to one startup transaction rather than repeating the same proof through each
wrapper. Required frozen checks remain in force.

Report verification phase, acknowledged launches, latest reconciled unit counts,
and stop reason separately. An alive process or high CPU use is not evidence of
coding. Older block totals must not replace newer partial-wave counts. Controller
terminal returns and accepted predictions differ when downstream checks fail.

Two identical incident fingerprints without new reconciled progress require a
different diagnosis or a precise blocker, not an identical relaunch. This is not
a token/time ceiling or permission to terminate a live worker. Preserve each
failure and name what new evidence or repair makes another operation useful.

On a researcher-requested pause, checkpoint, mark the operation paused, disable
only authorized project schedulers, and keep the restart pointer current. Do not
pursue an earlier production goal after the task changes.

## Update safety

`bootstrap.py --update --dry-run --json` previews conflicts. The install manifest
records baseline SHA-256 hashes. Modified kit-owned files and differing files
with unknown legacy baselines are preserved. Never adopt modified bytes as a
clean baseline merely to force an update.

Before updating an active run, create `project/ELARA_PROTECTED_PATHS.json` with
`schema_version: "1.0"` and `bindings`, an object mapping project-relative paths
to approved SHA-256 hashes. Include the controller, restricted worker definition,
runtime, and every kit-owned file bound by the run. Bootstrap retains bindings
and reports conflicts rather than overwriting them. Removing protection requires
separate reviewed migration. Report installed workflow and preserved execution
overrides separately; a version string is not byte-for-byte parity.
