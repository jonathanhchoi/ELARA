# One-unit subagent fan-out contract

Use this contract whenever a canonical stage requires many independent model judgments or
retrievals. Two kinds of fan-out share it:

- **Coding and audit fan-outs** (Stage 11 is the primary use; Stages 08, 12, and 15 reuse it for
  pilots, interpretive audits, and robustness conditions): one frozen coding or audit unit per
  worker, controlled by `scripts/unit_fanout.py`. Stage 14 consumes the merged data and does not
  use this contract for ordinary deterministic statistical analysis.
- **Research fan-outs** (Stage 02 query, author, citation-chain, and retrieval waves; Stage 07
  independent critics; Stage 19 claim-citation pairs; add-citations retrieval; fresh reviews under
  `fresh-review.md`): one bounded search, retrieval, critique, or review unit per worker,
  controlled by `scripts/research_fanout.py`.

## The host orchestrates; the kit validates

The host's own orchestrator runs the parallel workers. New runs use a bounded rolling pool,
never serial work in the parent context and never an all-tools default agent:

- **Claude Code** runs every fan-out as one of the kit's saved dynamic workflows —
  `.claude/workflows/elr-observation-fanout.js` for coding and audit units,
  `.claude/workflows/elr-research-fanout.js` for research units. The assistant launches the workflow
  itself as part of the stage (the Workflow tool with the workflow's `name` and structured `args`, or
  the `/elr-observation-fanout` and `/elr-research-fanout` commands the saved scripts provide); the
  researcher does not need to type anything, and their choice of ELARA's pipeline or of the stage is
  the opt-in to run the kit's workflows. The workflow runtime manages concurrency, tracks every
  agent, and lets a stopped run resume within the session; the researcher can watch it in
  `/workflows`.
- **Codex** runs every fan-out as the kit's custom sub-agents — `elr_worker` and
  `elr_research_worker`, defined in `.codex/agents/` — spawned by name by the parent session, one per
  assignment, with completed slots refilled individually using the host's own sub-agent tools
  (spawn, wait, and explicit close when offered; otherwise verified automatic release on native
  terminal completion; a CSV batch
  fan-out tool when the host offers one that can run the kit's restricted agents). The one parent
  stage goal supplies persistence and the native stage plan records progress; sub-agents supply
  parallelism. See `workflow/shared/execution-control.md`.
- **Either host**: the kit's controllers (`scripts/unit_fanout.py`, `scripts/research_fanout.py`)
  fix the manifest on disk, say what is pending, validate returns, bound attempts, and merge — the
  same scientific files whichever host ran the assignments. Resume evidence is the files under the run directory, so
  a fan-out that a session or host crash interrupted continues in the next session with the same
  command. If the host's orchestrator is unavailable, the fallback is never a serial imitation
  inside the parent's own context: on Claude Code (workflows disabled, or a host older than
  2.1.154) launch the same restricted worker types directly, one assignment per call, under the
  same manifest, and record the route as a limitation; on Codex (sub-agents disabled) stop with
  `waiting_for_user` and ask the researcher to enable sub-agents — a host setting only they can
  change — or, where the accepted pilot fixed an API route as the instrument, run that route.

## Scheduling policy and admission

Newly prepared coding, audit, research, critique, retrieval, and review runs use
`scripts/fanout_dispatch.py` for operational scheduling records while the host
still launches every restricted worker. Keep the policy outside the frozen
scientific assignments. Runs without a recorded policy use their original
scheduler; installing an update does not migrate a run or authorize a resume.

The default starts with at most six workers. At each passing batch checkpoint,
the stage parent may increase the target by one for the next dispatch session when
eligible backlog remains and at least the session target number of workers have
cleanly reconciled, up to twelve. It must explicitly record the passed
scientific, evidence, budget, and stop-rule checks before requesting that increase.
Worker completion, a workflow verifier, reconciliation, or closing a session does
not establish a passing scientific checkpoint or grow the target. Respect lower host capacity, researcher limits, frozen
instrument limits, and shared service limits. A positive explicit `concurrency`
is a fixed ceiling and disables automatic increases; provider throttling may still
reduce the effective target below that ceiling. Verify available worker
slots after reserving capacity for the parent and controller agents; do not infer
capacity from a product name or advertised maximum. Hold the target fixed within
a session. Confirmed provider throttle/backoff evidence halves the effective target (rounded down, minimum
one) for the next session, wait through two passing checkpoints before further
growth, and honor the service's retry delay. Do not use labels,
outcome frequencies, or substantive findings to choose concurrency.

Refill a completed slot promptly while other workers continue. Approved batch
sizes, research rounds, retry eligibility, cost ceilings, and researcher-selected
checkpoints still bound admission; do not dispatch the next batch early. Validate
returns and make shared writes serially. A checkpoint that requires a stop stops
refill immediately; reconcile the live workers under the existing time-box and
recovery rules. Unknown worker finality, a failed admission operation, or ambiguous
ownership never counts as a free slot or permission to launch the unit again.

Before admitting work, the parent opens an owned dispatch session with the exact
run directory, kind, available capacity, and any accepted block/limit. The helper
reserves ordered, assignment-specific tickets, not worker launches. On Codex,
the parent records native launch intent before spawning and acknowledgement only
after the host accepts an identifiable worker. Claude's saved workflow exposes a
completed agent result rather than a native acceptance handle: preserve the planned
ticket, use its worker start receipt as evidence of actual execution, and record
completed native evidence only after the awaited result. Do not manufacture an
acknowledgement or a never-started disposition from missing workflow output.
Each fresh worker must run
`python scripts/fanout_dispatch.py start --ticket <ticket-path>` before reading
scientific assignment content. A successful response contains only its own
assignment identity and paths. After the canonical return exists, it runs
`python scripts/fanout_dispatch.py finish --ticket <ticket-path>`; coding submit
may already have recorded this return. These helper-mediated writes are narrowly
permitted, never permission to read or edit the scheduler registry. A failed or
refused start ends that worker without reading, coding, fetching, or retrying.
Controller-only discovery and verification agents do not start scientific tickets.
The parent performs full controller integrity checks at dispatch-session and validation
boundaries. Each worker guard rehashes the ticket's common manifest, seal, specification,
and frozen-input bindings plus its own assignment or brief; it does not scan sibling
assignments and returns while holding the admission lock. Closed sessions move into
immutable hashed segments whose history is authenticated before a later session opens;
the active admission record must not replay the entire corpus on every worker call.

Each ticket, observed intent or acknowledgement, start, return, validation, and
checkpoint must reconcile from disk; unavailable native evidence remains explicitly
unobservable. Use native evidence for the exact ticket when a worker
stops without a return; a host completion alone proves neither a valid return nor
retry eligibility. Preserve all unknown attempts and pause affected admission.
An explicitly paused existing run may adopt this policy only through reviewed,
opt-in migration under `operational-recovery.md`, never by replacing its seals.


When the parent has confirmed provider throttling, record it through
`python scripts/fanout_dispatch.py reconcile --run-dir <run-dir> --owner <owner>
--throttled --retry-after-seconds <observed-seconds>`, together with any exact native
completion evidence. Preserve the provider evidence that supplied the delay. The
helper blocks new session admission, launch intents, and worker starts until the
latest recorded deadline has passed. If the provider gives no verifiable wait,
omit `--retry-after-seconds`: admission stays blocked for an unknown backoff, with
no guessed restart time. After verifying provider availability from new native
evidence, the parent may run `python scripts/fanout_dispatch.py resolve-backoff
--run-dir <run-dir> --owner <owner> --evidence-sha256 <availability-evidence-hash>`.
This never shortens a still-active known Retry-After deadline or resolves an
unknown worker's finality. Existing workers may finish and preserve their returns;
the parent retains the existing checkpoint, ownership, and resume rules.

## Freeze before fan-out

1. Freeze and hash the unit roster, codebook, task instructions, schema, source representation,
   model and effort, retry policy, terminal statuses, batch size, cost ceiling, and run code.
   Revalidate the specification, every frozen input, and every generated assignment before each
   status check, dispatch session, merge, or analysis; any drift stops the run.
2. Build an immutable assignment manifest with one row or JSON object per attempt. Each entry
   names a unique `assignment_id`, stable `unit_id`, assignment kind, attempt number, exact frozen
   input hashes, and one unique worker-return path. A coding unit may contain one document or
   several related documents; an interpretive-audit unit is one already-coded observation.
3. Validate that identifiers and return paths are unique, every path stays inside the allocated
   run directory, and no worker return path names a shared ledger, manifest, state file, aggregate
   dataset, or another worker's file.
4. Run a small accepted pilot through the same adapter and validators before scale-up. Do not
   switch between API and subagent routes without treating the route as part of the instrument.

## Worker isolation

Give each subagent one new, non-forked context and exactly one assignment. Do not inherit the
parent conversation, earlier answers, or another worker's context. Where the native spawn schema
supports it, explicitly set `fork_turns: "none"`; otherwise verify the host's equivalent fresh-context
behavior. A named restricted role alone does not establish context isolation. If the host cannot
exclude the parent conversation, pause that route under the existing capability rules. Include
only the applicable frozen instructions, schema, unit metadata, and that unit's authorized source
content or locator. Do not include earlier
answers, outcome counts, human gold labels, another worker's reasoning, or prior verifier findings.
Disable or forbid memory, web, and unrelated file inspection unless the frozen method explicitly
requires them. A shared filesystem is not statistical independence; workers must be told not to
read sibling assignments, worker returns, aggregates, or ledgers, and this residual limitation must
be reported when the platform cannot enforce filesystem isolation.

A coding or audit worker must not write its return path directly. It constructs one return envelope in memory and
sends that JSON on standard input to `python scripts/unit_fanout.py submit --run-dir <run-dir>
--assignment-id <assignment-id>`. The controller revalidates the sealed manifest, assignment hash,
IDs, schema, and unique path before creating the file, refuses every overwrite, and emits only an
operational receipt. The envelope must preserve the assignment and unit IDs, attempt number,
terminal status, structured result or typed error, and observable provenance. The worker returns
only that short operational receipt to the orchestrator, never the substantive label. Workers never
merge data, update shared ledgers, edit code, change state, retry themselves, or decide that a failed
unit should be dropped.

Strict submission prevents an invalid or duplicate envelope from becoming the canonical return; it
does not by itself sandbox the host. Use platform permissions or trusted deterministic hooks to deny
web, unrelated MCP tools, sibling reads, and out-of-scope writes where the platform can enforce
them. If those controls are unavailable, retain and disclose the residual shared-filesystem limit.

## Worker tool surface, time boxes, and crash-resume (every parallelized stage)

This section binds every stage that fans work out to parallel workers — the coding and audit
fan-outs above and equally the research fan-outs. It exists because of an incident, not a
hypothesis: on 2026-08-17 a background search worker launched as an all-tools default agent met a
403 bot wall on SSRN, opened the page in the Claude desktop app's in-app browser, and the app's GPU
process crashed eight seconds later, killing every session and worker and corrupting a file
mid-write; relaunched identically, it did the same thing again.

1. **Fixed, minimal tool surface, enforced by the platform.** Two worker types ship with the kit,
   defined once per host: on Claude Code `.claude/agents/elr-worker.md` and
   `.claude/agents/elr-research-worker.md` (`tools:` allowlist, `disallowedTools: mcp__*`), on Codex
   `.codex/agents/elr-worker.toml` (`elr_worker`) and `.codex/agents/elr-research-worker.toml`
   (`elr_research_worker`) (`developer_instructions`, `sandbox_mode`, no MCP servers). `elr-worker`
   / `elr_worker` (coding/audit, and the controller `status` steps of the workflows): read the
   assignment and source, run the controller's `submit`; no web, no writes to the run directory
   beyond the submit controller and its assigned dispatch start/finish helper. `elr-research-worker` / `elr_research_worker` (search, retrieval,
   critique, review): web fetch and search plus read/write of its own return path. Neither can reach
   an interactive surface — the host's in-app browser, computer use, desktop or other MCP tools,
   sub-agent spawning, user prompts, task or scheduling tools. The saved workflows set these
   `agentType`s; a Codex parent spawns these names; a fallback direct launch sets the matching
   `subagent_type`. Never launch a worker as a general-purpose or default agent. Claude Code loads
   a project's first `.claude/agents/` directory only at session start: after installing or
   updating the kit into a folder that had none, restart once before fanning out. On Codex, confirm
   at Stage 00 (and record in the access snapshot) that the host lists the kit's custom agents. If
   a named role or required hook is missing, or native policy rejects a required command, first
   diagnose the exact invocation's working root, active configuration layers, loaded roles and
   hooks, and (on Windows) effective native sandbox backend under `operational-recovery.md`.
   Apply supported invocation-scoped operational repairs under existing authority. Use a built-in
   worker only when the selected route already authorizes that fallback, with the same developer
   instructions and enforced restrictions, and record the residual limitation. Never substitute
   a frozen named role; an unresolved change to the approved route follows its existing decision process.
2. **Bot walls, paywalls, and rate limits are typed access gaps.** A worker that meets a 401/403/429,
   CAPTCHA, "verifying you are human" page, or login wall records `{url, status_or_message,
   timestamp_utc}` and moves on — one retry at most for a 429, no spoofing, no other surface. Sites
   known to sit behind bot walls (SSRN's `papers.ssrn.com`, HeinOnline, Westlaw, Lexis, JSTOR,
   Google Scholar) are reached only through open APIs and indexes (OpenAlex, CrossRef, Semantic
   Scholar, repository OAI/JSON endpoints, web-search snippets) or through the researcher's own
   authorized session, never by a worker. The parent aggregates the gaps after the research round. In Stage
   02 it first applies the parent-only browser fallback below to materially relevant download gaps;
   every unresolved gap then goes into the access-limitations record and manual search packet.
3. **Time boxes and timeouts.** Every worker gets a time box (default 12 minutes for a search or
   retrieval unit, 10 for a coding unit), stated in its brief or assignment; every network call
   inside it carries a hard timeout (about 60 s; 90 s for a full-text download); workers never
   sleep, poll, or wait more than about 30 s in total. Neither host runtime kills a worker on the
   time box for the kit, so the box is enforced by the worker's own bounded calls and by the
   parent's watch: a worker still running well past its box is stopped from the host's run view
   (`/workflows` on Claude Code; the agent thread controls on Codex) or by the assistant. An
   authorized time box remains binding unless the researcher changes it. Preserve the timeout,
   handle state, and original assignment and attempt; reconcile finality and retry eligibility
   under the frozen controller before another launch. An absent return or elapsed time alone
   never creates a new attempt. Keep affected dispatch stopped while finality or retry eligibility
   is unresolved, following `operational-recovery.md`.
4. **Crash-resume from disk.** Every fan-out lives under the run directory — never in the
   assistant's session scratchpad, which changes with the session: the sealed manifest (one row per
   assignment: id, kind, brief or assignment file, unique return path), the briefs or assignments,
   the workers' returns (written incrementally by research workers, `"complete": false` until the
   end; created once by the controller for coding workers), and the append-only launch record.
   The controllers derive what is pending from those files alone, so a run interrupted by a host
   or session crash resumes only after reconciling tickets, native handles, and returns from disk.
   Attempts are bounded: the coding controller allows the linked retry its policy names
   (`unit_fanout.py retry`); the research controller records each launch and stops offering an
   assignment after `max_attempts` (default 3), reporting it as `exhausted`; `--include-exhausted`
   adds diagnostics but never reuses an immutable return path. Additional authorized work starts a
   new explicitly versioned fan-out wave, and every exhausted assignment is surfaced in the stage's
   limitations, never silently dropped.
5. **Bounded concurrency and checkpoints.** Follow the recorded scheduling policy above.
   On either host, refill individual completed slots within the accepted batch or research round;
   use the session's fixed target and lower effective capacity. Legacy runs retain their recorded
   scheduler until explicitly migrated. The parent validates returns from files, merges serially,
   and appends a ledger checkpoint with exact counts. During Stage 11, disposition of each failed,
   invalid, or exhausted unit follows `workflow/stages/11-scale-up.md` and `guardrails.md` §11:
   decide under frozen rules and append to `failure_decisions.jsonl` when the preference is absent
   or `autonomous`; stop refill at the detecting checkpoint when it is `interactive`, reconcile
   live assignments, and present the pending failures. Only the parent appends that log, serially.
   Writes to manifests, merged aggregates, ledgers, and state are atomic (temporary file, then
   replace). At validation checkpoints scan for unexpected writes, including the repository root
   and working directory. Assigned returns, controller-created attempt files, and the helper-owned
   dispatch records are expected; arbitrary worker scratch files are not. Record each containment
   finding with its path and disposition, remove or quarantine it, and stop admission if it repeats.
   Tool restrictions do not by themselves bound every shell write. At launch and checkpoints,
   report exact terminal, active, and outstanding counts, elapsed time, retries, and an ETA range.
   Before measured throughput exists, use a range based on assignment durations, the recorded
   worker target, and checkpoint overhead. Thereafter use observed completed-assignment throughput
   and remaining work, including required batch drains. Record the helper's start-to-return registration metrics and refill delay when observable.
   Average registered workers and reconciled attempts per minute are operational estimates,
   not measurements of active model inference, token throughput, or native process liveness. Send an operational update about every five minutes where the host
   permits. Never expose interim labels or outcome distributions.

## Research fan-outs

A research fan-out is a directory under the stage's run directory (for example
`project/sources/preemption/<run_id>/fanout/queries_w1/`; one directory per wave or kind), laid out
and sealed by `scripts/research_fanout.py`:

```text
spec.json          contract_version, fanout_id, kind, time_box_minutes, max_attempts,
                   assignments: [{assignment_id, brief}]           (written by the parent)
briefs/<id>.md     one brief per assignment                          (written by the parent)
manifest.json      sealed by `prepare`: one row per allowed attempt, with brief hash,
                   attempt number, and unique return path; immutable
manifest.csv       the same attempt rows as CSV (for audit and parent tooling, not wholesale dispatch)
seal.json          hash of manifest.json; `status` fails closed on drift
returns/<id>__attempt-NNN.json
                   the worker's return: {"assignment_id", "attempt", "complete": true|false, ...}
attempts.jsonl     append-only launch rows; ticketed runs record only actual worker starts
dispositions.jsonl append-only parent records for failed or stage-schema-unusable attempts
```

The parent writes the briefs and `spec.json`, runs `python scripts/research_fanout.py prepare
--fanout-dir <dir>`, and hands the directory to the host orchestrator. A brief carries everything the
worker needs and nothing it must not see: the frozen instructions for that one unit (the verbatim
query and routes; the author or work; the claim-citation pair; the artifact and sources under
review), the return schema for the `result` field, the time box, and the tool and access-gap rules
above — never other workers' findings, running tallies, or the verdict the stage is heading toward.
The worker's return is a JSON object with `assignment_id`, `attempt`, `complete`, and the stage's
`result` fields, plus `access_gaps` and timestamps. The controller validates assignment identity,
attempt identity, and operational completion; the stage validates the rest when it merges.
`status --include-pending` lists eligible attempts and their paths without recording a launch.
For a policy-enabled run, reserve through the dispatch helper and record each research launch
only when that worker passes its start guard. The legacy `--record-launch` route remains for
unmigrated runs. `status` alone reports assignment states (`expected`, `complete`,
`incomplete`, `missing`, `invalid`, `exhausted`, and `pending`) plus an attempt-level reconciliation
of `attempted`, `succeeded`, `failed`, `unusable`, and `outstanding`. Keep those denominators
distinct in the run ledger.

When a return says `complete: true` but fails the brief's stage-specific schema, the parent does not
edit, move, or overwrite it. It records the terminal attempt with `python
scripts/research_fanout.py record-disposition --fanout-dir <dir> --assignment-id <id> --attempt
<number> --terminal unusable --reason <exact validation failure>`, then runs `status
--include-pending` to inspect the next controller-authorized sealed attempt. Reserve it through
the dispatch helper for policy-enabled runs; a status listing is not a launch. Use terminal `failed` for
a launched worker or route that failed without a usable result. Once all sealed attempts are used,
the assignment stays exhausted; start a new explicitly versioned fan-out wave if the research design
authorizes more work. `--include-exhausted` reports diagnostic details but never reopens or reuses a
return path. The controller does not offer the next path while the latest launch is missing,
incomplete, or invalid but undisposed, because that worker may still be writing; the parent must
record the exact terminal reason first. The parent, never a worker, validates and merges successful
returns deterministically in assignment and attempt order and appends the ledger checkpoint.

## Parent-only browser fallback for Stage 02

Browser control is a serial access-remediation step in the parent literature-review session, never
a worker tool and never a retry of a fan-out assignment in the parent's context. After validating
and merging each Stage 02 wave, the parent applies this protocol to every typed access gap for a
work that could materially affect the closest-work map, a citation chain, or the verdict:

1. Recheck the exact title and locator through lawful open routes first: the publisher or repository
   landing page, an author or institutional copy, and any available purpose-built scholarly
   connector, API, or index. Do not use a browser merely to repeat a route that already succeeded.
2. If full text is still blocked by an automated-download or bot restriction, classify the host
   before touching any browser. A host is **challenge-evidenced** when any automated fetch in the
   same project met a 403, a CAPTCHA, a bot challenge, or a "verifying you are human" page there,
   or when it is a known challenge-fronted or walled host (`papers.ssrn.com`, HeinOnline, Westlaw,
   Lexis, JSTOR, Google Scholar, `academic.oup.com`, and other Cloudflare-fronted publisher
   sites). Never open a challenge-evidenced host in the host application's own in-app browser
   pane: a challenge page rendering there has crashed the desktop host about one second after
   loading — the interstitial's GPU probe (a WebGPU `requestAdapter()` call) killed the app's GPU
   process faster than any tool round trip could close the tab (workers twice on 2026-08-17;
   parent fallback attempts on 2026-08-26 and 2026-08-30) — so no react-and-navigate-away rule
   can execute in time, and avoidance is the only defense. Route a challenge-evidenced source to
   the researcher's own real, separate-process browser session where the platform exposes one
   (for example the Claude Code Chrome extension connection, used with the researcher's
   awareness), or straight to the manual search packet. For a host with no challenge evidence,
   the parent uses browser control in the researcher's main session, opens the exact landing URL,
   and makes one bounded ordinary-UI attempt to open or download the work — on Claude Code as one
   batched action sequence (navigate, one bounded text read, then immediately a blank page), so
   that no unknown page rests in the in-app pane across a tool round trip. An existing
   signed-in session may be used only when the project's recorded authorization permits that source.
   Never inspect credentials or session stores, spoof a client, disable protections, solve or bypass
   a CAPTCHA, evade a paywall or terms, or manufacture a direct-download URL.
3. If the page requires a login, CAPTCHA, license acceptance, purchase, or other action only the
   researcher can take, leave the control with the researcher and batch the exact requests under
   `guardrails.md` section 11. Browser unavailability or a failed ordinary-UI attempt is evidence of
   an access gap, not permission to switch to an unsupported automation route. If a challenge or
   interstitial verification page ("checking your browser", "just a moment") appears despite the
   host classification above, that attempt is over and the host is challenge-evidenced for the
   rest of the project: record the access gap, leave the page at once if the pane still responds,
   and never wait on, reload, retry, or interact with such a page — and expect no second chance,
   because the recorded crashes followed the page's render faster than an agent can react. A
   crashed session resumes from the files but loses the researcher's time.
4. Record one `search_log.csv` row with route `parent_browser_fallback` for each attempted source:
   source ID, landing URL, original status or message and time, browser-attempt time, browser surface,
   final URL when visible, and result (`retrieved`, `still_blocked`, `researcher_action_required`, or
   `browser_unavailable`). If a potentially material gap is not attempted because use is not
   authorized, the host is challenge-evidenced, or the locator is not a lawful retrieval route,
   record that typed reason instead.
5. A successful browser download is not self-validating. Save or copy the lawful full text into the
   Stage 02 `retrieved/` directory, verify that it is the identified work rather than an HTML
   challenge or error page, hash it, and update the source manifest with retrieval surface, access
   date, local path, hash, and full-text-read status. Only then may the work become verified.

This fallback does not change worker isolation, fan-out counts, or saturation rules. The parent
keeps browser attempts serial so interactive state and downloaded files cannot race, and the manual
search packet contains every source that remains unresolved after the protocol.

## Codex adapter

For interruption handling and cross-session checkpoints, also read
`workflow/shared/operational-recovery.md`. The lifecycle journal is an optional,
explicitly adopted addition, never a replacement for the frozen controller or
host-native restricted-worker route. Do not infer launch eligibility from a
missing return or replay an unacknowledged launch without resolving finality.

Codex runs the fan-out as the kit's custom sub-agents (`.codex/agents/`), spawned by name by the
parent session with the host's own sub-agent tools; the parent never processes assignments in its
own context and never launches a general-purpose or `default` sub-agent for kit work.

1. The parent uses an authorized goal covering the canonical stage's completion contract and native
   plan under `workflow/shared/execution-control.md`, including its equivalent-goal and
   foreground-fallback rules. If goal activation is available but no covering goal is active, return to the
   stage handoff and give `/goal <goal_condition>`; do not create a narrower fan-out goal. The
   stage goal covers all assignments, serial validation, merge, and final verification. Workers never
   create goals or plans.
2. For a policy-enabled run, open a session with
   `python scripts/fanout_dispatch.py open-session --run-dir <run-dir> --kind coding|research
   --owner <native-session-id> --host codex --capacity <available-worker-slots>` and the recorded
   optional `--concurrency`, `--block`, or `--limit`. Dispatch only the returned reserved tickets,
   in order, up to the target. Before each spawn, run `intent --ticket <ticket-path> --owner <owner>`;
   after positive host acceptance, run `ack --ticket <ticket-path> --owner <owner>
   --evidence-sha256 <native-acknowledgement-hash>` through the same helper. Give a fresh
   `elr_worker` or `elr_research_worker` a non-forked context (explicit `fork_turns: "none"`
   where supported, or the verified native equivalent), only its own start command and frozen
   settings, then its one assignment or brief through the successful receipt. Never embed scientific content ahead
   of the start guard. Wait only on acknowledged handles. When the native runtime confirms a
   worker is terminal, close its handle if the host offers an explicit close operation. If the
   host has no close operation, accept automatic slot release only after verifying that its
   capacity limit counts active workers and terminal completion releases that capacity. A
   terminal thread may remain available for follow-up without occupying an active slot; never
   use that thread for another assignment. Reconcile the exact ticket and canonical return
   serially, confirm the runtime has capacity for a fresh worker, then refill without waiting
   for unrelated workers. Missing close tooling alone is not a route failure; unknown native
   finality or unverified capacity still stops admission. Record the host's release behavior
   with the runtime capability evidence.
   Run `reconcile --run-dir <run-dir> --owner <owner>` and `close-session` using the same run
   and owner. After all required stage validation, evidence, budget, and stop-rule checks pass,
   the stage parent explicitly records the checkpoint decision with
   `python scripts/fanout_dispatch.py checkpoint --run-dir <run-dir> --owner <owner> --passed`.
   This requires a closed session; completion receipts and workflow verification alone never
   authorize adaptive growth. Without `--passed`, checkpoint snapshots operational state only
   (recorded throttling may still reduce the next target). The helper checks actual eligible
   backlog, clean reconciliation count, capacity, and cooldown; the next session uses its stored target. Reconcile native evidence with `--host-evidence`
   when needed: a JSON list of objects containing `ticket_id`, `status` (`completed`,
   `never_started`, or `unknown`), and `evidence_sha256`. `never_started` requires positive exact
   evidence and no accepted or started record; it is never inferred from a missing return.
   Use `--stop-admissions` when a native call fails or has an ambiguous outcome. Correct rejected
   calls and reconcile stops under `operational-recovery.md`; do not allocate scientific retries
   in the scheduler. If open reports `mode: legacy`, keep the run's original bounded-wave route
   unless the researcher explicitly adopts a reviewed migration. Each coding worker uses the
   controller's `submit`, never direct return-path writes. Never reuse a context for another unit.
3. A CSV batch fan-out tool (the host reads a CSV, spawns one worker per row, and collects results
   — `spawn_agents_on_csv` in Codex as of 2026-08) may run coding assignments from the coding controller's
   active assignment rows only when its workers can be given the kit's restricted agent, or when the
   parent has confirmed for that turn that the sandbox denies network and no MCP or browser tools are
   configured, and records that in the run manifest. Never dispatch a research `manifest.csv`
   wholesale: it includes sealed but unused retry slots. Research workers receive only the current
   `pending_assignments` returned by `research_fanout.py status`; otherwise spawn the named agents
   directly. For policy-enabled runs, a CSV route must preserve ticket start guards, individual
   completion/reconciliation, the recorded concurrency policy, and native launch evidence; if it
   cannot, use direct restricted-worker spawning.
4. Discover the session's actual sub-agent capacity and whether the kit's custom agents are loaded;
   do not assume a portable default. The manifest and ledger, not conversation memory, determine
   what remains; every worker return path stays under the run directory.

Field names of the custom-agent files (`name`, `description`, `developer_instructions`,
`sandbox_mode`, `mcp_servers`) and the tool names above are the host's schema as of 2026-08 — a
dated default under `guardrails.md` §10: Stage 00 records the host version and what it actually
lists, and the invariants above (restricted worker, one unit per fresh context, manifest on disk,
bounded concurrency and attempts, serial merge) hold whatever the host calls its knobs.

## Claude Code adapter

Claude Code v2.1.154 or later runs the kit's saved dynamic workflows; the assistant launches them
itself as part of the stage — with the Workflow tool, giving the workflow's `name` and structured
`args`, or by the slash command each saved script provides — and the researcher's choice of ELARA's
pipeline or of the stage is the opt-in for that. No permission mode change is needed. Quote paths
containing spaces.

- **Coding and audit units**: `elr-observation-fanout` with `{ "run_dir": "<run-dir>" }` (optional
  `block`, `limit`, `concurrency`, `model`, `effort`; `fixture: true` only for an explicit kit validation
  fixture). One discovery agent runs the controller's `status`, then one `elr-worker` per pending
  assignment submits through the controller, then an operational verifier runs `status` again.
  `/elr-code-observations` validates the handoff first when the researcher invokes it explicitly.
- **Research units**: `elr-research-fanout` with `{ "fanout_dir": "<prepared-fan-out-directory>" }`
  (optional fixed `concurrency`, `limit`, `include_exhausted`, `model`, `effort`). A discovery
  agent opens the session and fresh `elr-research-worker` instances run ticketed assignments
  in a rolling pool. Record a research launch when its worker actually starts, never by marking
  the entire pending list launched in advance. The verifier reconciles and closes the operational
  session; the stage parent separately approves the scientific checkpoint. A legacy
  run retains its prior workflow path.
- Policy-enabled workflows require a stable native-session `owner`; pass verified available
  worker `capacity` after controller/parent reserve, including values below six. If omitted,
  capacity defaults conservatively to six. The recorded target is fixed within that batch/session;
  optional `concurrency` sets a fixed ceiling; recorded provider backoff can lower the effective target. Preserve `block`, `limit`, model, and effort
  constraints. Each invocation admits at most 998 workers, reserving two of the runtime's 1,000
  agent calls for discovery and verification. Continue remaining work in a reconciled later
  session without crossing an approved batch or research-round boundary. Existing workflow
  arguments still work for legacy runs without a scheduling policy.
  For the first invocation of an explicitly migrated paused run, the parent also supplies
  `resume_request` and `request_root`: paths to the reviewed `resume_dispatch` decision request
  and its project root. The workflow passes them to that same discovery `open-session` call.
  Do not pre-open a session and then ask a workflow to replay its tickets; an existing session
  returns no new tickets and requires reconciliation instead.
- Claude's saved workflow does not expose structured provider-throttle or Retry-After evidence.
  A null result or host exception stops admission and preserves the uncertainty; it never becomes
  a rate-limit diagnosis by parsing raw error text. A research site's HTTP 429 is an access gap,
  not evidence that the model provider has throttled the worker pool. The parent must obtain
  actual native provider evidence before recording a provider backoff or changing its duration.
- Every agent runs as the kit's restricted `agentType`, so the tool surface is enforced by the
  platform. Workflow agents run with the researcher's tool allowlist: the first `python
  scripts/unit_fanout.py …` or `research_fanout.py …` command and the first web fetch may prompt
  once; approving them for the project lets the rest of the run proceed without prompts. The first
  launch of a saved workflow asks whether to allow it; "don't ask again for this workflow in this
  project" permits a run of many assignments. The runtime's `Large workflow` notice past
  25 agents is advisory — a coding run's scale is fixed by the manifest, not by the size guideline
  Claude uses when it writes new workflows.
- The runtime runs at most 16 agents concurrently and 1,000 per run; a 500-unit job fits but
  should still be piloted for cost and permission behavior (start with `limit` or `block`).
  Resume within the session replays finished agents from the runtime's journal; across sessions,
  resume evidence is the completed return files, so relaunching the same workflow after a crash
  continues where the files left off. If `CLAUDE_CODE_SUBAGENT_MODEL` is set it overrides the
  workflow's model for every worker: record it in the run manifest as capability drift.
- Only when workflows are unavailable (disabled, or a host older than 2.1.154) may the assistant
  launch workers directly with the Agent tool, one assignment per call, `subagent_type`
  `elr-worker` or `elr-research-worker`, under the same manifest, scheduling policy, and controllers — and it
  records that route in the run manifest.

## Serial validation and resumption

As workers complete, the parent process—not a worker—must validate IDs, schema, quotations,
allowed statuses, frozen hashes, and path scope. Archive invalid returns and create a new linked
attempt under the frozen retry rule; never overwrite. Update shared ledgers and manifests serially.
Interim status may reveal only operational counts, failures, retries, time, and cost. Do not reveal
label frequencies or other outcomes that could affect stopping or repair decisions.

Resume from validated terminal return files plus the durable ledger. Treat an absent, malformed,
or unvalidated return as outstanding. When all assignments are terminal, reconcile the roster,
attempts, failures, hashes, and unique output paths; merge deterministically in manifest order;
and have a fresh reviewer (per `fresh-review.md` in this directory) inspect the chain from source to
assignment to return to aggregate.

## Provenance and limits

Record the platform, route, requested and reported model when observable, effort and sampling
settings or `unobservable`, host version, dispatch/start/completion timestamps, scheduling policy,
actual concurrency, checkpoint identity, prompt and input hashes,
request IDs, usage, latency, errors, retries, skill/contract hash, and repository revision. Never
claim that a subagent run is the same wire request as an API call: host system instructions, tool
definitions, context, sampling controls, and model snapshots may differ. Validate end-to-end route
equivalence empirically and describe unobservable fields honestly.
