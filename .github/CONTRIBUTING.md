# Developing ELARA

This file is for work on ELARA itself, in a plain clone of
`jonathanhchoi/ELARA`. It is not installed into research projects, and a
research session never acts on it.

## Fixes are made here, never inside a project

Research sessions run ELARA as installed and never change it (see "Research
sessions run ELARA; they never change it" in
`workflow/shared/operational-recovery.md`). When ELARA's machinery fails in a
project, the assistant re-runs the failed command once, tries one documented
smaller route, and then writes `project/kit_issues/kit_issue_<UTC timestamp>.md`.
Those reports, usually filed as
[GitHub issues](https://github.com/jonathanhchoi/ELARA/issues), are the input
to work here. A fix reaches projects through the normal stage-start update.

## How to fix an incident

- Prefer removing the failure mode, or adding a fallback that the "When
  something breaks" steps can use (a documented smaller route, a clearer
  `doctor.py` message), over adding a rule.
- Do not answer an incident with a new verification requirement, proof step,
  review, or approval for research sessions. Each of those becomes recurring
  engineering in every project.
- When a rule is truly needed, replace or delete an existing one. Keep the
  research-facing rules in `AGENTS.md`, `CLAUDE.md`, and `workflow/shared/`
  short, and put maintainer detail here.
- Never weaken a scientific invariant to make a fix easier: gates, frozen
  instruments, worker isolation and restrictions, quote anchoring, immutable raw
  outputs, exact denominators, blinding, preregistration, and audit separation.

## Keep the research-facing rules small

- `workflow/shared/` may hold at most 60 KiB (61,440 bytes) in all;
  `tests/test_workflow.py` fails CI past that. A new rule replaces or removes an
  existing one. A fix should remove a failure or add a fallback, not add a new
  verification step.
- `AGENTS.md` (always loaded on both hosts) states the core rules; the shared
  files add only the detail it lacks, and a stage-specific procedure belongs in
  its stage file. Methods references that are not rules, such as the
  measurement-error guide, live in `workflow/guides/`.
- Incident history and host internals belong here, not in the shared rules.

## Incidents behind current rules

These were moved out of the shared rules in 2.19.0; the rules keep only what to
do.

- **Workers run only as restricted types.** On 2026-08-17 a background search
  worker launched as an all-tools default agent met a 403 bot wall on SSRN,
  opened the page in the Claude desktop app's in-app browser, and the app's GPU
  process crashed eight seconds later, killing every session and worker and
  corrupting a file mid-write. Relaunched identically, it did the same again.
- **Challenge-evidenced hosts never open in the in-app pane.** Parent fallback
  attempts on 2026-08-26 and 2026-08-30 crashed the desktop app about one
  second after a challenge page rendered: the interstitial's GPU probe (a
  WebGPU `requestAdapter()` call) killed the GPU process faster than any tool
  round trip could close the tab, so avoidance is the only defense.
- **Workers hand in a draft file.** Passing the return envelope on the command
  line or through a heredoc exceeded Windows' 32,000-character limit (2.16.0).
- **Exports are deliverables plus one zip per run, at stage ends.** Before
  2.19.0 the agent exported loose files at batch checkpoints: one project made
  162 exports holding 138,067 files (57 exports in one day), single exports
  reached 9,000–12,000 files, and each copy to Drive took 20–35 minutes.
- **Updates never block a stage.** A conflicted update used to stop every new
  stage until someone repaired the installation, which invited hand repair of
  kit files inside projects. Since 2.19.0 the stage runs on the installed
  version; only an update interrupted part-way waits.

## Checks before a pull request

```text
python scripts/validate_workflow.py
python scripts/sync_skill_wrappers.py --check
python scripts/check_docs.py
python -m unittest discover -s tests
git diff --check
```

Generated wrappers come from `scripts/sync_skill_wrappers.py`; edit its
templates and regenerate rather than editing a wrapper. Bump
`workflow_version` in `project/PROJECT_STATE.md` and
`tests/fixtures/clean_project_records/PROJECT_STATE.md`, and add a version note
to `PIPELINE.md`.

## Diagnostic notes from past host failures

Before 2.15.0, the research-facing recovery rules told the assistant to
diagnose host failures itself. These notes, moved here verbatim, are for kit
development only; read "repair" in them as a change made in this repository.

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
