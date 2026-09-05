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

The parallel wave itself is run by the host's own orchestrator, never by the assistant launching
workers one at a time by hand and never by an all-tools default agent:

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
  assignment, in bounded waves, with the host's own sub-agent tools (spawn, wait, close; a CSV batch
  fan-out tool when the host offers one that can run the kit's restricted agents). The one parent
  stage goal supplies persistence and the native stage plan records progress; sub-agents supply
  parallelism. See `workflow/shared/execution-control.md`.
- **Either host**: the kit's controllers (`scripts/unit_fanout.py`, `scripts/research_fanout.py`)
  fix the manifest on disk, say what is pending, validate returns, bound attempts, and merge — the
  same files whichever host ran the wave. Resume evidence is the files under the run directory, so
  a fan-out that a session or host crash interrupted continues in the next session with the same
  command. If the host's orchestrator is unavailable, the fallback is never a serial imitation
  inside the parent's own context: on Claude Code (workflows disabled, or a host older than
  2.1.154) launch the same restricted worker types directly, one assignment per call, under the
  same manifest, and record the route as a limitation; on Codex (sub-agents disabled) stop with
  `waiting_for_user` and ask the researcher to enable sub-agents — a host setting only they can
  change — or, where the accepted pilot fixed an API route as the instrument, run that route.

## Freeze before fan-out

1. Freeze and hash the unit roster, codebook, task instructions, schema, source representation,
   model and effort, retry policy, terminal statuses, batch size, cost ceiling, and run code.
   Revalidate the specification, every frozen input, and every generated assignment before each
   status check, worker wave, merge, or analysis; any drift stops the run.
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

Give each fresh subagent exactly one assignment. Include only the applicable frozen instructions,
schema, unit metadata, and that unit's authorized source content or locator. Do not include earlier
answers, outcome counts, human gold labels, another worker's reasoning, or prior verifier findings.
Disable or forbid memory, web, and unrelated file inspection unless the frozen method explicitly
requires them. A shared filesystem is not statistical independence; workers must be told not to
read sibling assignments, worker returns, aggregates, or ledgers, and this residual limitation must
be reported when the platform cannot enforce filesystem isolation.

The worker must not write its return path directly. It constructs one return envelope in memory and
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
   beyond the controller's own. `elr-research-worker` / `elr_research_worker` (search, retrieval,
   critique, review): web fetch and search plus read/write of its own return path. Neither can reach
   an interactive surface — the host's in-app browser, computer use, desktop or other MCP tools,
   sub-agent spawning, user prompts, task or scheduling tools. The saved workflows set these
   `agentType`s; a Codex parent spawns these names; a fallback direct launch sets the matching
   `subagent_type`. Never launch a worker as a general-purpose or default agent. Claude Code loads
   a project's first `.claude/agents/` directory only at session start: after installing or
   updating the kit into a folder that had none, restart once before fanning out. On Codex, confirm
   at Stage 00 (and record in the access snapshot) that the host lists the kit's custom agents; if it
   does not, spawn the host's built-in worker with the same developer instructions pasted from the
   TOML file and record the residual limitation.
2. **Bot walls, paywalls, and rate limits are typed access gaps.** A worker that meets a 401/403/429,
   CAPTCHA, "verifying you are human" page, or login wall records `{url, status_or_message,
   timestamp_utc}` and moves on — one retry at most for a 429, no spoofing, no other surface. Sites
   known to sit behind bot walls (SSRN's `papers.ssrn.com`, HeinOnline, Westlaw, Lexis, JSTOR,
   Google Scholar) are reached only through open APIs and indexes (OpenAlex, CrossRef, Semantic
   Scholar, repository OAI/JSON endpoints, web-search snippets) or through the researcher's own
   authorized session, never by a worker. The parent aggregates the gaps after the wave. In Stage
   02 it first applies the parent-only browser fallback below to materially relevant download gaps;
   every unresolved gap then goes into the access-limitations record and manual search packet.
3. **Time boxes and timeouts.** Every worker gets a time box (default 12 minutes for a search or
   retrieval unit, 10 for a coding unit), stated in its brief or assignment; every network call
   inside it carries a hard timeout (about 60 s; 90 s for a full-text download); workers never
   sleep, poll, or wait more than about 30 s in total. Neither host runtime kills a worker on the
   time box for the kit, so the box is enforced by the worker's own bounded calls and by the
   parent's watch: a worker still running well past its box is stopped from the host's run view
   (`/workflows` on Claude Code; the agent thread controls on Codex) or by the assistant, its
   assignment stays pending on disk, and the next run of the fan-out picks it up as a new attempt.
4. **Crash-resume from disk.** Every fan-out lives under the run directory — never in the
   assistant's session scratchpad, which changes with the session: the sealed manifest (one row per
   assignment: id, kind, brief or assignment file, unique return path), the briefs or assignments,
   the workers' returns (written incrementally by research workers, `"complete": false` until the
   end; created once by the controller for coding workers), and the append-only launch record.
   The controllers derive what is pending from those files alone, so a run interrupted by a host
   or session crash resumes in any later session by launching the same workflow or wave again.
   Attempts are bounded: the coding controller allows the linked retry its policy names
   (`unit_fanout.py retry`); the research controller records each launch and stops offering an
   assignment after `max_attempts` (default 3), reporting it as `exhausted`; `--include-exhausted`
   adds diagnostics but never reuses an immutable return path. Additional authorized work starts a
   new explicitly versioned fan-out wave, and every exhausted assignment is surfaced in the stage's
   limitations, never silently dropped.
5. **Bounded concurrency and checkpoints.** The host runtime bounds concurrency (Claude Code's
   workflow runtime: at most 16 agents at once and 1,000 per run; Codex: the session's
   `[agents]` thread cap); the kit's research workflow additionally runs its workers in waves of six
   at once by default (`concurrency` argument) because research workers usually share
   rate-limited APIs, and the coding workflow accepts the same argument for a shared, rate-limited
   model route. On Codex the parent spawns at most six workers per wave (fewer under a shared
   rate limit), waits for the whole wave, and only then spawns the next. After each run or wave
   the parent validates returns from files, merges serially, and appends a ledger checkpoint with
   exact counts. During the Stage 11 coding run, the disposition of each failed, invalid, or
   exhausted unit found at these checkpoints follows the researcher's recorded `failure_handling`
   preference as `workflow/stages/11-scale-up.md` and `workflow/shared/guardrails.md` §11 direct:
   decide under the frozen rules, append the judgment to the run's `failure_decisions.jsonl`, and
   continue when the preference is absent or `autonomous`; pause at the checkpoint and present
   the pending failures when it is `interactive`. Only the parent appends that log, serially.
   Writes to manifests, merged aggregates, ledgers, and state are atomic (temporary
   file, then replace); the controllers already write that way. After every wave, the parent
scans for files created during the wave outside the run directory's expected paths (worker
returns, attempts, seals, and the parent's own `failure_decisions.jsonl`) — the repository root
and working directory included. Any stray
worker write is a containment finding: record it in the run ledger with the file's path and
disposition, remove or quarantine it, and treat repetition as a stop condition for the wave
in either failure-handling mode.
Tool restrictions bound what a worker may invoke, not where a shell may write; only this scan
closes that gap. At launch and after each status
   check or wave, the parent tells the researcher the exact terminal and outstanding counts,
   elapsed wall-clock time, retries or exhausted assignments, and a revised time-remaining range.
   Before measured throughput exists, base the provisional range on the number of waves and worker
   time boxes; afterward use observed wall-clock wave throughput and the actual remaining waves.
   If a wave runs longer than about five minutes, give the same operational update from the host's
   run view at about five-minute intervals where the host permits. Never expose interim labels or
   other substantive outcomes in these updates.

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
attempts.jsonl     append-only launch rows written by `status --record-launch`
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
`status --include-pending --record-launch` lists what to launch, including its attempt-specific path,
and records the launch. `status` alone reports assignment states (`expected`, `complete`,
`incomplete`, `missing`, `invalid`, `exhausted`, and `pending`) plus an attempt-level reconciliation
of `attempted`, `succeeded`, `failed`, `unusable`, and `outstanding`. Keep those denominators
distinct in the run ledger.

When a return says `complete: true` but fails the brief's stage-specific schema, the parent does not
edit, move, or overwrite it. It records the terminal attempt with `python
scripts/research_fanout.py record-disposition --fanout-dir <dir> --assignment-id <id> --attempt
<number> --terminal unusable --reason <exact validation failure>`, then runs `status
--include-pending --record-launch` to obtain the next sealed attempt path. Use terminal `failed` for
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

1. The parent must already be running the canonical stage's exact front-matter goal and native
   plan under `workflow/shared/execution-control.md`. If that goal is not active, return to the
   stage handoff and give `/goal <goal_condition>`; do not create a narrower fan-out goal. The
   stage goal covers every wave, serial validation, merge, and final verification. Workers never
   create goals or plans.
2. Each wave: run the controller's `status --include-pending` (with `--record-launch` for a
   research fan-out) to obtain the pending list; spawn one `elr_worker` (coding/audit) or
   `elr_research_worker` (research) per pending assignment, up to six at once and never more than
   the session's thread cap, each with a message naming exactly its one assignment or brief and its
   attempt number and unique return path (plus the frozen model and effort where the host lets a spawn set them); wait for
   the whole wave; close the workers; run `status` again; append the ledger checkpoint; update
   the parent native plan with the exact counts; repeat
   until nothing is pending. Never reuse a worker context for another unit. Each coding worker
   uses the controller's `submit` rather than writing the return path directly.
3. A CSV batch fan-out tool (the host reads a CSV, spawns one worker per row, and collects results
   — `spawn_agents_on_csv` in Codex as of 2026-08) may run a coding wave from the coding controller's
   active assignment rows only when its workers can be given the kit's restricted agent, or when the
   parent has confirmed for that turn that the sandbox denies network and no MCP or browser tools are
   configured, and records that in the run manifest. Never dispatch a research `manifest.csv`
   wholesale: it includes sealed but unused retry slots. Research workers receive only the current
   `pending_assignments` returned by `research_fanout.py status`; otherwise spawn the named agents
   directly.
4. Discover the session's actual sub-agent capacity and whether the kit's custom agents are loaded;
   do not assume a portable default. The manifest and ledger, not conversation memory, determine
   what remains; every worker return path stays under the run directory.

Field names of the custom-agent files (`name`, `description`, `developer_instructions`,
`sandbox_mode`, `mcp_servers`) and the tool names above are the host's schema as of 2026-08 — a
dated default under `guardrails.md` §10: Stage 00 records the host version and what it actually
lists, and the invariants above (restricted worker, one unit per fresh context, manifest on disk,
bounded waves and attempts, serial merge) hold whatever the host calls its knobs.

## Claude Code adapter

Claude Code v2.1.154 or later runs the kit's saved dynamic workflows; the assistant launches them
itself as part of the stage — with the Workflow tool, giving the workflow's `name` and structured
`args`, or by the slash command each saved script provides — and the researcher's choice of ELARA's
pipeline or of the stage is the opt-in for that. No permission mode change is needed. Quote paths
containing spaces.

- **Coding and audit units**: `elr-observation-fanout` with `{ "run_dir": "<run-dir>" }` (optional
  `block`, `concurrency`, `model`, `effort`; `fixture: true` only for an explicit kit validation
  fixture). One discovery agent runs the controller's `status`, then one `elr-worker` per pending
  assignment submits through the controller, then an operational verifier runs `status` again.
  `/elr-code-observations` validates the handoff first when the researcher invokes it explicitly.
- **Research units**: `elr-research-fanout` with `{ "fanout_dir": "<prepared-fan-out-directory>" }`
  (optional `concurrency` — default six — `limit`, `include_exhausted`, `model`, `effort`). One
  discovery agent runs the controller's `status --include-pending --record-launch`, then one
  `elr-research-worker` per pending assignment reads its brief and writes its return, in waves,
  then an operational verifier runs `status` again.
- Every agent runs as the kit's restricted `agentType`, so the tool surface is enforced by the
  platform. Workflow agents run with the researcher's tool allowlist: the first `python
  scripts/unit_fanout.py …` or `research_fanout.py …` command and the first web fetch may prompt
  once; approving them for the project lets the rest of the run proceed without prompts. The first
  launch of a saved workflow asks whether to allow it; "don't ask again for this workflow in this
  project" is the right answer for a run of many waves. The runtime's `Large workflow` notice past
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
  `elr-worker` or `elr-research-worker`, under the same manifest, waves, and controllers — and it
  records that route in the run manifest.

## Serial validation and resumption

After each bounded wave, the parent process—not a worker—must validate IDs, schema, quotations,
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
settings or `unobservable`, host version, timestamps, concurrency wave, prompt and input hashes,
request IDs, usage, latency, errors, retries, skill/contract hash, and repository revision. Never
claim that a subagent run is the same wire request as an API call: host system instructions, tool
definitions, context, sampling controls, and model snapshots may differ. Validate end-to-end route
equivalence empirically and describe unobservable fields honestly.
