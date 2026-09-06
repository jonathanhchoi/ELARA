# Check ELARA before starting new work

Before each new stage or optional tool, the parent checks the installed ELARA
against `jonathanhchoi/ELARA` on GitHub, branch `main`. Latest means the exact
commit observed at that boundary. Never use the research project's Git remote
as upstream. Maintaining ELARA itself is not a research-stage invocation.

## When to check

- Check before Stage 00, selected stages or tools, automatic transitions, and
  new recovery runs of completed stages. Recheck after a long pause before a
  run begins. Routing, status, help, and menu-only requests stay read-only.
- Existing runs resume under their recorded software, without checks per
  batch or retry. Independently reviewed migration under existing scoped
  authority follows `operational-recovery.md`; updates never silently migrate
  frozen research execution.
- Only the parent checks. Restricted workers never contact GitHub or update
  the kit. No research material is sent with the check.

## Check, repair or update, verify

1. Run the read-only `python scripts/check_update.py --stage <canonical-stage>
   --json`. `ready: true` / exit 0 establishes usable installation evidence,
   subject to research prerequisites. The checker hashes installed files every
   time; a release label or previous successful check is insufficient.

2. Under the default automatic-update policy, an available compatible update
   needs no repeated approval. Explain the change briefly and run
   `python scripts/check_update.py --stage <canonical-stage> --auto-update
   --json` when writes are authorized. This checks again, downloads its
   exact commit, uses the protected installer's clean preflight, installs only
   that target, and verifies the result. Compatibility means a conflict-free
   ownership/protection preview and successful installation checks, not merely
   a larger version number. Honor explicit researcher limits on updating.
   During Plan Mode use the read-only check; defer installation until execution.
   When it reports `update_available` with a verified `installed_commit`, the
   assistant may conduct the read-only plan using those installed instructions.
   Record the pending update in the plan; do not allocate a run, write project
   state, or execute the stage. On leaving Plan Mode, install and verify the
   update, reread its instructions, and reconcile the plan before execution.
   This limited planning exception does not claim `ready: true` or require a
   separate update approval. Unverified or conflicted bytes require investigation.

3. If GitHub is unavailable, continue with `status: verified_installed` only
   when the checker freshly verifies a completed installation's exact commit
   and full recorded file inventory, or a clean official Git checkout. Record
   that upstream currency was not checked and retry at the next stage boundary.
   Never call this result current on GitHub. A ZIP or legacy label without
   authenticated installed bytes cannot use the fallback; obtain its source
   identity or restore service first. A transient outage is not a permission
   problem and does not justify recreating monitoring.

4. Missing/modified files, protected conflicts, unknown baselines, or unfinished
   installations enter autonomous repair. Preview with `bootstrap.py --update
   --ref <full-commit> --dry-run --json`, inspect the conflict, and preserve
   every researcher file and run binding. Ask only if resolving it requires a
   genuine researcher choice after existing instructions have been reconciled.
   A declined specific change remains binding, but do not invent a general
   approval requirement from a recoverable conflict. Never adopt modified bytes
   as a clean baseline or remove protection merely to get a passing check.

5. Require `ready: true`, successful bootstrap/doctor verification, and no
   `project/ELARA_UPDATE_PENDING.json`. The installer preserves project state,
   logs, models, prompts, codebooks, schemas, and protected execution files.
   Files removed upstream are retained as conflicts until reviewed. Rerun the
   workflow validator and wrapper check, complete the nonblocking model-readiness
   advisory, and reread updated `AGENTS.md`, this contract, and the canonical
   stage. Reload host definitions when required, preserving the pending stage.
   A successful installation does not authorize a scientific amendment.

6. The checked exact commit governs this stage entry. Do not loop indefinitely
   because main advanced during installation or require a second approval.
   The next new stage gets a fresh check. If an installation fails, inspect its
   durable evidence rather than repeat the same operation without a repair.

## Records and interrupted installations

`project/ELARA_MANIFEST.json` records source identity, installed commit, complete
installation status, file ownership, and baseline hashes separately from the
project's historical `workflow_version`. Before changing files, an update writes
`project/ELARA_UPDATE_PENDING.json` and removes it only after verification.
An interruption leaves that marker; inspect and complete the exact update,
never clear the marker just to advance or claim a partial installation current.

Keep check output in the conversation during read-only planning. Once writing
is authorized, archive it as `kit_update_check.json` in the new run directory
and reference it in the run manifest. Record the actual policy/authority and
exact target commit for an update, including whether installed fallback was
used. Do not allocate a run or alter state merely to record a Plan Mode check.

This is an executable prerequisite invoked by the parent, not an operating-system
lock. Compatible automatic updates and verified installed fallback are defaults;
an explicit researcher restriction overrides them. Neither default changes
scientific approvals or corpus retry eligibility.
