# Behavioral acceptance scenarios

Run these scenarios in fresh temporary copies of the kit. Never use a live research project as a
forward-test target.

1. **Plan produces no writes.** Invoke a `plan_then_execute` stage in Plan Mode. The task returns a
   decision-complete plan and exact execution handoff; a before/after file hash inventory matches.
2. **Missing prerequisite stops safely.** Set `current_stage` to `08-pilot` without approved design
   artifacts. The stage names the missing versions and leaves state unchanged.
3. **Authorization refusal is terminal.** Deny data authorization at stage 06. State remains
   `awaiting_approval`; no source text is transmitted or processed.
4. **Reruns append.** Run one fixture stage twice. The second run creates `_v002` and a new ledger
   entry; `_v001` remains byte-identical.
5. **Corpus deviation returns to preregistration.** Introduce a material coverage shortfall at stage
   10. The stage records a deviation and routes to stage 09 instead of silently continuing.
6. **Validation failure loops backward.** Supply failing human-validation metrics. Stage 13 records
   the disposition and routes to stage 05 or 08; it does not run confirmatory analysis.
7. **Fresh-session resume.** Start a new task after a completed fixture stage and invoke `elr`.
   The router reads state and selects the next stage without relying on conversation memory.
8. **Replication is self-contained.** Extract the final fixture package into a clean directory and
   run its documented rebuild command. All reported fixture values are reproduced from archived
   inputs and outputs.
9. **Fan-outs are host-managed.** Prepare the one-unit fixture (`scripts/unit_fanout.py prepare`
   on `fixtures/one_unit_fanout/spec.json`) and a one-brief research fan-out
   (`scripts/research_fanout.py prepare`). In Claude Code, the stage launches the saved
   `elr-observation-fanout` / `elr-research-fanout` workflows itself (visible in `/workflows`) and
   every agent runs as `elr-worker` / `elr-research-worker`; in Codex, the parent spawns
   `elr_worker` / `elr_research_worker` by name in bounded waves. In neither host does the assistant
   launch a general-purpose agent, hand-launch workers one at a time, or process units in its own
   context; a stopped run relaunched with the same command resumes from the return files, and the
   controllers' `status` reconciles the counts.

The machine-readable cases in `fixtures/stage_contract_cases.json` record the profile, gate,
success transition, and at least one valid failure route for every canonical stage 00–19.
`test_acceptance.py` checks those records against the canonical front matter, exercises clean-copy
and Download-ZIP discovery for both Codex and Claude, and runs the no-network public-domain fixture
twice: once to build the package and once from that package in a fresh directory.
