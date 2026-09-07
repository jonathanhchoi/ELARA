# Restarting coding without changing the research

Read this with Stage 11 and `observation-fanout.md`. The host still launches
restricted workers; `unit_fanout.py` still validates, retries, and merges.
`scripts/fanout_lifecycle.py` is a provider-neutral journal, not a launcher,
scientific validator, source of retry permission, or replacement model route.

## Reconcile authority before requesting a decision

Current user instructions govern the concrete action. Read applicable standing
decisions and their scope, limits, revocations, and later changes before asking.
An assistant-written handoff, seal, scope file, or waiting state records authority;
it cannot independently narrow or expand it. A researcher-supplied handoff can
contain a real limit, which a later explicit instruction can supersede. Preserve
both records and explain the prospective effect. A single-use runtime does not
make standing recovery authority single-use.

Routers and host adapters use `scripts/recovery_decision.py` for the same closed
decision. Its `decide(root, request)` API and `--root ... --request ...` CLI are
read-only. Requests identify the action, run, scientific binding hash, all
applicable researcher instructions (source path, SHA-256, exact quote, scope),
current restrictions, and evidence references. The parent must accurately
interpret those instructions and include every applicable limit; hashing a quote
cannot establish its meaning or create consent. Do not supply a permission
boolean or treat a helper's result as independent research authorization.

- `proceed`: the action is covered and its required operational evidence exists.
- `repair`: investigate or complete missing verification under existing scope;
  dispatch remains stopped. Independent review, testing, and sealing are work
  for the assistant, not new requests for researcher approval.
- `wait_external`: record a verified external capability problem and preserve
  the checkpoint. Do not relaunch unchanged work or recreate monitoring unless
  requested. A timeout while a handle remains live is still a live operation.
- `request_user`: a concrete researcher decision remains, such as missing or
  exhausted authority, a revoked instruction, scientific change, or unresolved
  corpus-attempt eligibility. Ask once for that decision and its actual source.

Required evidence is separate for offline boundary tests, live capability,
independent review, activation review, unchanged scientific bindings, preserved
history, exclusive ownership, and reconciled attempts. The helper verifies
hash-bound summary receipts; their producers must derive each finding from the
actual operation and preserve underlying evidence. It does not validate research
results or allocate retries. An adapter must enforce the decision before its
own dispatch checks, not merely display it in a report.

Before rewriting routing state, preserve the outgoing bytes, append the current
decision, clear only resolved inputs, and validate state. Optional
`recovery_decision` binds request/result references so the validator can reproduce
the decision and reject stale routing. Use existing `active_artifacts` and
`run_checkpoint` fields; do not invent competing top-level routing pointers.

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
old run sealed implementation bytes, record independently reviewed operational
migration before changing the entrypoint. Existing scoped researcher authority
can cover that migration after scientific bindings and preserved history are
verified; do not ask again merely because the implementation changed. Never
weaken the old seal, discard history, or change corpus retry eligibility.

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
Capability and production must exercise the same command-construction and hook
transport implementation with their authorized configuration differences made
explicit. Check the actual downstream arguments and installed host's event
contract. A configuration key appearing in a file proves neither acceptance nor
enforcement. A startup warning alone is not a failed permission gate. Review the
diagnostic assumptions alongside the repair and keep those observations separate.

Bind each worker and helper interpreter explicitly to the reviewed, tested runtime
configuration and record its executable in the manifest. Before launch, reject any
setup-selected interpreter that differs from that binding and repair the mismatch
under existing authority. If setup uses `sys.executable`, verify its value instead of
silently inheriting the setup environment's default. Exercise the required read,
write, or submit operation with the bound interpreter in the actual restricted
worker or helper context. Successful setup, printed arguments, or the presence of
an operating-system application alias do not establish readiness in that context.
Preserve failed-boundary evidence; a failed read alone does not prove that an
interpreter alias caused it.

For an isolated Codex invocation, inspect its effective working root, active
configuration layers, and loaded agent and hook sources. `--ignore-user-config`
omits the user configuration file while retaining the authentication location
([official CLI reference](https://learn.chatgpt.com/docs/developer-commands#codex-exec)).
Project configuration and hooks load only for a trusted project; review of an
individual hook's definition is separate from loading its source
([configuration](https://learn.chatgpt.com/docs/config-file/config-advanced#project-config-files-codexconfigtoml),
[hooks](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks)).
Omitting user settings may therefore explain lost role or hook discovery when
those settings supplied the required configuration or project trust. Treat this
as a diagnostic inference to test, not a proven cause of every host failure.
Under existing scoped authority, prefer supported invocation-only corrections
for the approved workspace and reviewed hook definitions; do not persist broad
trust changes or weaken the approved restrictions. A hook-trust option does not
establish that a project source loaded. For the corrected synthetic check, use a
fresh, single-use runtime through the actual command construction. Retain earlier
failure evidence and verify the required named role and lifecycle events before
resuming dispatch.

On Windows, configuration isolation can also omit native sandbox settings.
Verify the effective backend and explicitly bind the invocation to one supported
by the installed host, preserving the approved filesystem and network restrictions
and approval policy. In Codex 0.149.1, an unmatched command is forbidden under
`Never` when the Windows backend is `Disabled` and managed filesystem restrictions
exclude full-disk write access ([exec-policy check, lines 730–766](https://github.com/openai/codex/blob/ff29a44391deccde0aba0f8390337d7f3c319ea4/codex-rs/core/src/exec_policy.rs#L730-L766),
[restriction predicate, lines 817–824](https://github.com/openai/codex/blob/ff29a44391deccde0aba0f8390337d7f3c319ea4/codex-rs/core/src/exec_policy.rs#L817-L824)).
Distinguish an evidenced native policy rejection from a researcher refusal;
diagnose and repair within existing scope. Do not enable approval prompts, bypass
the sandbox, or broaden access merely to force a probe through. Configuration text
and a matching source branch do not establish readiness: complete the existing
fresh synthetic round-trip through the actual restricted worker operation.

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

Before new stages, follow `kit-updates.md`; continuing an already-started run
preserves its recorded software. `--require-clean` refuses known conflicts before
installation. `project/ELARA_UPDATE_PENDING.json` identifies an update that has
not completed verification. Never clear it or relabel a partial installation as
current to permit a new stage. `installed_commit` is separate from the requested
source version; the checker verifies the recorded installed files as well.

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
