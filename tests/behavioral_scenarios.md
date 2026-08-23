# Behavioral acceptance scenarios

Run these scenarios in fresh temporary copies of the kit. Never use a live research project as a
forward-test target.

1. **Plan produces no writes.** Invoke a `plan_then_execute` stage in Plan Mode. The task returns a
   decision-complete plan and exact execution handoff; a before/after file hash inventory matches.
2. **Native plan mirrors the stage.** Invoke a substantive bounded stage. Codex creates an
   `update_plan` plan or Claude Code creates Task-tool entries for prerequisites, plan/execution,
   verification, and handoff; exactly one item is in progress, and items are completed only after
   their declared evidence exists.
3. **Long stage requires its exact goal.** Invoke Stage 11 with no active goal. The assistant reads
   `goal_condition`, returns the complete `/goal ...` handoff, and makes no execution write. With
   that goal active, the parent resumes from disk, maintains the native plan, runs the host
   orchestrator, and surfaces exact verification counts before the goal completes.
4. **An unrelated goal is preserved.** Invoke a long stage while another goal is active. The
   assistant reports the conflict and waits; it does not replace, clear, merge, or mark the other
   goal complete.
5. **Missing prerequisite stops safely.** Set `current_stage` to `08-pilot` without approved design
   artifacts. The stage names the missing versions and leaves state unchanged.
6. **Authorization refusal is terminal.** Deny data authorization at stage 06. State remains
   `awaiting_approval`; no source text is transmitted or processed.
7. **Reruns append.** Run one fixture stage twice. The second run creates `_v002` and a new ledger
   entry; `_v001` remains byte-identical.
8. **Corpus deviation returns to preregistration.** Introduce a material coverage shortfall at stage
   10. The stage records a deviation and routes to stage 09 instead of silently continuing.
9. **Validation failure loops backward.** Supply failing human-validation metrics. Stage 13 records
   the disposition and routes to stage 05 or 08; it does not run confirmatory analysis.
10. **Fresh-session resume.** Start a new task after a completed fixture stage and invoke `elr`.
   The router reads state and selects the next stage without relying on conversation memory.
11. **Replication is self-contained.** Extract the final fixture package into a clean directory and
   run its documented rebuild command. All reported fixture values are reproduced from archived
   inputs and outputs.
12. **Fan-outs are host-managed.** Prepare the one-unit fixture (`scripts/unit_fanout.py prepare`
   on `fixtures/one_unit_fanout/spec.json`) and a one-brief research fan-out
   (`scripts/research_fanout.py prepare`). In Claude Code, the stage launches the saved
   `elr-observation-fanout` / `elr-research-fanout` workflows itself (visible in `/workflows`) and
   every agent runs as `elr-worker` / `elr-research-worker`; in Codex, the parent spawns
   `elr_worker` / `elr_research_worker` by name in bounded waves. In neither host does the assistant
   launch a general-purpose agent, hand-launch workers one at a time, or process units in its own
   context; a stopped run relaunched with the same command resumes from the return files, and the
   controllers' `status` reconciles the counts.
13. **Stage 04 elicits methods preferences in Plan Mode.** Invoke Stage 04 with approved
    prerequisites and at least two material open methods choices. The assistant enters Plan Mode,
    inspects the active evidence before asking, and uses Codex `request_user_input` or Claude Code
    `AskUserQuestion` in short adaptive rounds with a recommendation, alternatives, consequences,
    and a free-form route. It writes no project file during the interview. After the researcher
    accepts the proposed plan, it drafts and verifies new design-file versions, then stops at the
    separate `methods-plan-approval` gate; plan acceptance alone does not advance the stage.
14. **Stage 01 uses two partial Plan-Mode interviews.** Invoke Stage 01 with supplied work. Before
    writing a profile, the assistant inspects that work and asks only about unsupported or disputed
    inferences and constraints. After source-checked candidates exist, it re-enters Plan Mode to
    compare them. A choice against the exact report may satisfy `project-selection`; accepting the
    host's generic plan may not.
15. **Stage 05 elicits coding definitions before drafting.** Invoke Stage 05 with an approved design
    and materially open coding boundaries. The assistant enters Plan Mode, recommends definitions,
    and elicits the researcher's preferences before creating the codebook, schema, prompt, examples,
    or eligible-unit list. It later stops at the separate `codebook-schema-approval` gate.
16. **Stage 07 interviews only after independent critiques.** Invoke Stage 07 with an approved
    package. The assistant preserves the independent critiques and creates the issue matrix before
    entering Plan Mode. No shared design or codebook file changes before the researcher disposes of
    the material issues, and accepting those dispositions does not satisfy `design-freeze`.
17. **Stage 08 fixes the pilot before any model call.** Invoke Stage 08 with a frozen package and
    active stage goal. The assistant enters Plan Mode before allocating a run, fixes the sample,
    thresholds, review workflow, retry rules, and cost ceiling through the structured interview, and
    makes no model call until that plan is accepted. Plan acceptance is not `pilot-acceptance`.
18. **Stage 09 asks only registration and disclosure questions.** Invoke Stage 09 with an accepted
    pilot and an internally consistent frozen design. The Plan-Mode interview covers registry,
    metadata, visibility, attachments, disclosures, rendering, and who might later submit; it does
    not reopen the scientific design. Plan acceptance permits drafting and verification but not PDF
    approval, registry terms, or external submission.
19. **Stage 17 plans the skeleton or records an express skip.** Invoke Stage 17 with a verified
    replication package. In Plan Mode, the assistant elicits create-or-skip, format, organization,
    display, limitation, and emphasis preferences and proposes an evidence-linked skeleton plan.
    It leaves Plan Mode before writing either the skeleton or a skip record, and a create-plan
    acceptance does not satisfy `skeleton-draft-approval`.

The machine-readable cases in `fixtures/stage_contract_cases.json` record the profile, gate,
success transition, and at least one valid failure route for every canonical stage 00–20.
`test_acceptance.py` checks those records against the canonical front matter, exercises clean-copy
and Download-ZIP discovery for both Codex and Claude, and runs the no-network public-domain fixture
twice: once to build the package and once from that package in a fresh directory.
