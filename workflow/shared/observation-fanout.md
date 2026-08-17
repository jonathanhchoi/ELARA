# One-unit subagent fan-out contract

Use this contract when a canonical stage requires many independent model judgments. Stage 11
is the primary coding use; Stages 08, 12, and 15 reuse it for pilots, interpretive audits, and
robustness conditions. Stage 14 consumes the merged data and does not use this contract for
ordinary deterministic statistical analysis.

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
fan-outs above and equally the Stage 02 search waves, source retrieval, citation chains, cite-checks,
and fresh reviews. It exists because of an incident, not a hypothesis: on 2026-08-17 a background
search worker launched as an all-tools default agent met a 403 bot wall on SSRN, opened the page in
the Claude desktop app's in-app browser, and the app's GPU process crashed eight seconds later,
killing every session and worker and corrupting a file mid-write; relaunched identically, it did the
same thing again.

1. **Fixed, minimal tool surface, enforced by the platform.** Two worker types ship with the kit:
   `elr-worker` (coding/audit: read the assignment and source, run the controller's `submit`; no
   web, no writes to the run directory) and `elr-research-worker` (search/retrieval/review: web fetch
   and search plus read/write of its own output path). Neither can reach an interactive surface — the
   host's in-app browser, computer use, desktop or other MCP tools, sub-agent spawning, user prompts,
   task or scheduling tools. On Claude Code they are `.claude/agents/elr-worker.md` and
   `.claude/agents/elr-research-worker.md` (`tools:` allowlist, `disallowedTools: mcp__*`); launch
   workers with that `subagent_type`/`agentType`, never `general-purpose`. Note that Claude Code
   loads a project's first `.claude/agents/` directory only at session start: after installing or
   updating the kit into a folder that had none, restart once before fanning out. On Codex, give
   workers the same restricted instructions and use whatever tool restriction the platform offers;
   record the residual limitation if none is available.
2. **Bot walls, paywalls, and rate limits are typed access gaps.** A worker that meets a 401/403/429,
   CAPTCHA, "verifying you are human" page, or login wall records `{url, status_or_message,
   timestamp_utc}` and moves on — one retry at most for a 429, no spoofing, no other surface. The
   parent aggregates gaps into the stage's access-limitations record and manual search packet.
   Sites known to sit behind bot walls (SSRN's `papers.ssrn.com`, HeinOnline, Westlaw, Lexis, JSTOR,
   Google Scholar) are reached only through open APIs and indexes (OpenAlex, CrossRef, Semantic
   Scholar, repository OAI/JSON endpoints, web-search snippets) or through the researcher's own
   authenticated session, never by a worker.
3. **Time boxes and timeouts.** Every worker gets a time box (default 12 minutes for a search or
   retrieval unit, 10 for a coding unit); every network call inside it carries a hard timeout (about
   60 s; 90 s for a full-text download); workers never sleep, poll, or wait more than about 30 s in
   total.
4. **Crash-resume from disk.** The parent keeps a fan-out manifest under the run directory (one row
   per assignment: id, kind, prompt or assignment file, unique output path, attempt, launch time,
   status, note), workers write their outputs incrementally under the run directory (a partial
   return is marked `complete: false` and is not merged), and every brief, prompt, and merged
   aggregate lives under the run directory too — never in the assistant's session scratchpad, which
   changes with the session. Before each launch the parent runs a watchdog pass: a worker overdue by
   the time box plus a margin (default 15 minutes) is stopped, marked `timed_out`, and relaunched as
   a new attempt; after a bounded number of attempts (default 3) the assignment is recorded as
   failed and surfaced in the review's limitations, never silently dropped.
5. **Bounded concurrency and checkpoints.** Launch at most six workers at once (fewer when a shared
   rate-limited API is on every worker's route), wait for a wave, validate returns from files, merge
   serially, append a ledger checkpoint with exact counts, then launch the next wave. Writes to the
   manifest, merged aggregates, ledgers, and state are atomic (temporary file, then replace).

## Codex adapter

Use Goal mode for a long run. If Goal mode is not active, stop and give the researcher this handoff,
filled with the fixed paths and completion count:

`/goal Use $elr-code-observations to process <manifest>, one fresh subagent per assignment, in bounded waves. Preserve each unique return, validate and checkpoint serially, expose no interim outcomes, and finish only when the ledger reconciles to <N> terminal assignments.`

Discover the session's actual subagent capacity; do not assume a portable default. Spawn only the
available number of workers, wait for the whole bounded wave, validate returns from files, update
the ledger serially, and repeat. Never reuse a worker context for another unit. Goal mode supplies
persistence and completion criteria; the manifest and ledger, not conversation memory, determine
what remains. Each Codex worker uses the controller's `submit` command rather than writing the
return path directly.

## Claude Code adapter

Claude Code v2.1.154 or later can run the project workflow
`.claude/workflows/elr-observation-fanout.js`. Invoke the `/elr-code-observations` skill to validate
the handoff, then run `/elr-observation-fanout` with a structured `run_dir` argument. Quote paths
containing spaces; use `fixture: true` only for an explicit kit validation fixture. The workflow uses one discovery agent,
then `pipeline()` with one agent per pending assignment, then an operational verifier, every one of
them launched as the `elr-worker` subagent type so the tool surface is enforced by the platform. The workflow
runtime may run at most 16 agents concurrently and 1,000 total per run; a 500-unit job fits the
documented total cap but should still be piloted for cost and permission behavior. Resume evidence
comes from completed return files because workflow replay is only guaranteed within the same
Claude session. Research fan-outs that are not one-unit codings (Stage 02 searches and citation
chains, retrieval, cite-checks, fresh reviews) use the Agent tool directly with
`subagent_type: "elr-research-worker"`, one assignment per call, under the manifest, watchdog, and
concurrency rules of the section above.

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
