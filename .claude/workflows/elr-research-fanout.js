export const meta = {
  name: 'elr-research-fanout',
  description: 'Run one bounded empirical-legal-research assignment (search, retrieval, cite-check, review) per isolated research worker',
  whenToUse:
    'ELARA research fan-outs under workflow/shared/observation-fanout.md, "Research fan-outs": Stage 02 query, author, citation-chain, and retrieval assignments; Stage 07 independent critics; Stage 19 claim-citation pairs; add-citations retrieval; fresh reviews. After scripts/research_fanout.py prepare has sealed a fan-out directory, run the approved pending assignments as restricted elr-research-worker subagents. Launched by the assistant as part of the stage; the researcher does not need to type it.',
  phases: [
    { title: 'Discover', detail: 'controller dispatch: reserve the approved pending assignments' },
    { title: 'Workers', detail: 'one fresh elr-research-worker whenever a worker slot becomes free' },
    { title: 'Verify', detail: 'controller status again: complete / incomplete / missing / exhausted' },
  ],
}

// Accept the Workflow-tool `args` global when it is defined and non-null; otherwise fall
// back to a `workflowArgs` global provided by a saved-workflow host. String input keeps
// the JSON-parse branch below.
const rawInput =
  typeof args !== 'undefined' && args !== null ? args : globalThis.workflowArgs
let workflowArgs = rawInput
if (typeof workflowArgs === 'string') {
  try {
    workflowArgs = JSON.parse(workflowArgs)
  } catch {
    throw new Error('Pass JSON arguments such as {"fanout_dir":"<prepared-fan-out-directory>"}.')
  }
}
if (typeof workflowArgs !== 'object' || workflowArgs === null || typeof workflowArgs.fanout_dir !== 'string') {
  throw new Error('Pass { fanout_dir: "<prepared-fan-out-directory>" } (the directory scripts/research_fanout.py prepare sealed).')
}

// Two restricted worker types, both defined under .claude/agents/ so the platform enforces the tool
// surface (see workflow/shared/observation-fanout.md, "Worker tool surface, time boxes, and crash-resume"):
// - elr-worker (Read/Bash/Glob/Grep, no web) runs the controller commands in Discover and Verify;
// - elr-research-worker (web fetch and search plus read/write of its own output path; no browser,
//   computer-use, desktop, MCP, or user-prompt tools) performs the assignments.
// Optional model/effort passthrough applies to the research workers only.
const controllerOptions = { agentType: 'elr-worker' }
const workerOptions = { agentType: 'elr-research-worker' }
if (workflowArgs.model !== undefined && workflowArgs.model !== null) {
  workerOptions.model = workflowArgs.model
}
if (workflowArgs.effort !== undefined && workflowArgs.effort !== null) {
  workerOptions.effort = workflowArgs.effort
}

// Continuous sessions retain their approved target through this batch. Legacy sessions keep waves.
const concurrency = Number.isInteger(workflowArgs.concurrency) && workflowArgs.concurrency > 0
  ? workflowArgs.concurrency
  : null
if (workflowArgs.concurrency != null && concurrency === null) {
  throw new Error('concurrency must be a positive integer.')
}
const capacity = workflowArgs.capacity == null ? 6 : workflowArgs.capacity
if (!Number.isInteger(capacity) || capacity < 1) throw new Error('capacity must be a positive integer.')
if (workflowArgs.owner != null && (typeof workflowArgs.owner !== 'string' ||
    !workflowArgs.owner.trim() || workflowArgs.owner.length > 240)) {
  throw new Error('owner must be a nonempty stable identifier of at most 240 characters.')
}
if (workflowArgs.limit != null && (!Number.isInteger(workflowArgs.limit) || workflowArgs.limit < 1)) {
  throw new Error('limit must be a positive integer.')
}
// Reserve two of the runtime's 1,000 agent calls for Discover and Verify.
const limit = Math.min(workflowArgs.limit == null ? 998 : workflowArgs.limit, 998)
const limitFlag = ` --limit ${limit}`
const shellArg = value => "'" + String(value).replace(/'/g, "'\\''") + "'"
const runFlag = ` --run-dir ${shellArg(workflowArgs.fanout_dir)}`
const fanoutFlag = ` --fanout-dir ${shellArg(workflowArgs.fanout_dir)}`
const ownerFlag = workflowArgs.owner == null ? '' : ` --owner ${shellArg(workflowArgs.owner)}`
for (const key of ['resume_request', 'request_root']) {
  if (workflowArgs[key] != null && (typeof workflowArgs[key] !== 'string' || !workflowArgs[key].trim())) {
    throw new Error(`${key} must be a nonempty path.`)
  }
}
const resumeFlags = (workflowArgs.resume_request == null ? '' : ` --request ${shellArg(workflowArgs.resume_request)}`) +
  (workflowArgs.request_root == null ? '' : ` --request-root ${shellArg(workflowArgs.request_root)}`)
const exhaustedFlag = workflowArgs.include_exhausted === true ? ' --include-exhausted' : ''
const dispatchFlags = `${runFlag} --kind research --host claude --capacity ${capacity}${limitFlag}` +
  ownerFlag + resumeFlags + exhaustedFlag + (concurrency === null ? '' : ` --concurrency ${concurrency}`)

// The restricted worker definitions load from .claude/agents/ when Claude Code
// starts in this folder. When this session started elsewhere (or before the kit
// was installed), the platform reports the agent type as not found; translate
// that into the researcher-facing instruction the kit already documents.
const missingWorkerDefinitions = error =>
  /agent type '[^']+' not found/i.test(String((error && error.message) || error))
const restartAdvice = () =>
  new Error(
    "ELARA's restricted worker definitions (.claude/agents/) are not loaded in " +
    'this session, so parallel work cannot start. Claude Code loads them when ' +
    'the app starts in the project folder: restart the app there once, then run ' +
    'the stage again. The sealed assignments on disk are unchanged and nothing ' +
    'is lost.',
  )

phase('Discover')
let discovered
try {
  discovered = await agent(
  `Read workflow/shared/observation-fanout.md (the section "Research fan-outs"). Run the following command exactly ONCE, copying every identifier literally. Do not retry or correct
an already issued command; if it fails or differs from the requested command, report discovery failure.
python scripts/fanout_dispatch.py open-session${dispatchFlags}
Return its operational JSON unchanged when mode is continuous. Never record a launch during discovery
for a continuous run. The parent supplies a stable owner; never invent one, migrate a legacy run, or
override an active session. If and only if the command reports mode legacy, preserve its legacy protocol:
python scripts/research_fanout.py status${fanoutFlag} --include-pending --record-launch${limitFlag}${exhaustedFlag}
Return that command's counts and pending_assignments, with mode legacy added. Do not open briefs or
returns or report findings. On any command error return only
{"mode":"failed","status":"discovery_failure","error":"dispatch_failed_closed"}.
A command error never permits the legacy route; do not include raw error payloads.`,
  {
    label: 'discover-pending',
    schema: {
      type: 'object',
      required: ['mode'],
      properties: {
        mode: { type: 'string', enum: ['continuous', 'legacy', 'failed'] },
        tickets: { type: 'array', items: { type: 'object' } },
        target: { type: 'integer' },
        pending_assignments: {
          type: 'array',
          items: {
            type: 'object',
            required: ['assignment_id', 'attempt', 'brief_path', 'return_path'],
            properties: {
              assignment_id: { type: 'string' },
              attempt: { type: 'integer' },
              brief_path: { type: 'string' },
              return_path: { type: 'string' },
            },
            additionalProperties: true,
          },
        },
        expected: { type: 'integer' },
        complete: { type: 'integer' },
        exhausted: { type: 'integer' },
        time_box_minutes: { type: 'integer' },
      },
      additionalProperties: true,
    },
    ...controllerOptions,
  },
)
} catch (error) {
  if (missingWorkerDefinitions(error)) throw restartAdvice()
  throw error
}
if (discovered && (discovered.status === 'discovery_failure' || discovered.error)) {
  throw new Error('Dispatch discovery failed closed; inspect the controller operational record. No workers were launched.')
}
if (!discovered || !['continuous', 'legacy'].includes(discovered.mode)) {
  throw new Error('Dispatch discovery did not return a valid mode; no workers were launched.')
}
const continuous = discovered.mode === 'continuous'
const pending = continuous ? discovered.tickets : discovered.pending_assignments
if (!Array.isArray(pending) || pending.length > limit) throw new Error('Invalid or oversized dispatch batch.')
if (continuous && (typeof workflowArgs.owner !== 'string' || !workflowArgs.owner.trim())) {
  throw new Error('A continuous run requires the parent-supplied stable owner.')
}
if (continuous && discovered.owner !== workflowArgs.owner) {
  throw new Error('Dispatch discovery returned a different owner; no workers were launched.')
}
if (continuous && (discovered.reused_session !== false || discovered.state !== 'active')) {
  throw new Error('An existing or paused dispatch session must be reconciled; no worker was relaunched.')
}
if (continuous && (!Number.isInteger(discovered.target) || discovered.target < 1 ||
    discovered.target > capacity || (concurrency !== null && discovered.target > concurrency))) {
  throw new Error('The dispatch target exceeds the verified worker capacity or fixed concurrency.')
}
const seen = new Set()
const seenAssignments = new Set()
for (const item of pending) {
  const key = continuous ? item && item.ticket_id : item && item.assignment_id
  if (typeof key !== 'string' || seen.has(key) || typeof item.assignment_id !== 'string' ||
      !Number.isInteger(item.attempt) || typeof item.brief_path !== 'string' ||
      typeof item.return_path !== 'string' || seenAssignments.has(item.assignment_id) ||
      (continuous && typeof item.ticket_path !== 'string')) {
    throw new Error('Invalid or duplicate dispatch item.')
  }
  seen.add(key)
  seenAssignments.add(item.assignment_id)
}
log(`${pending.length} pending assignment(s); ${discovered.complete}/${discovered.expected} already complete; ${discovered.exhausted} exhausted`)

const workerPrompt = item => `You are one ELARA research worker under workflow/shared/observation-fanout.md. Do exactly one
assignment and nothing else.

1. Read your brief completely: ${item.brief_path}
   It contains the frozen instructions for this unit, the return schema, and the rules. Follow it exactly.
2. Write your structured return as UTF-8 JSON to this path and no other:
   ${item.return_path}
   This is attempt ${item.attempt}. The return must be a JSON object with
   "assignment_id": "${item.assignment_id}", "attempt": ${item.attempt}, and a boolean "complete".
   Write it early with "complete": false, rewrite it after each completed step or route, and rewrite it a
   last time with "complete": true when the assignment is finished. Never write any other file.
3. Time box: ${discovered.time_box_minutes} minutes. Every network call carries a hard timeout; never
   sleep, poll, or wait more than about 30 seconds in total.
4. A 401/403/429, CAPTCHA, "verifying you are human" page, or login wall is a typed access gap
   (record url, status or message, UTC time) — move on; at most one retry for a 429; never spoof or
   escalate to another surface. You have no browser, computer-use, desktop, or MCP tools; do not try.
5. Do not read sibling briefs or returns, ledgers, aggregates, or project state. Record only what you
   actually retrieved; never invent or complete a citation, quotation, count, or URL.

Reply with your assignment_id, attempt number, the output path, whether the return is complete, and one line of
operational summary (counts, gaps, time) — no findings.`

const ticketPrompt = item => `Your FIRST operation, before reading any brief or retrieving a source, must be:
python scripts/fanout_dispatch.py start --ticket ${shellArg(item.ticket_path)}
Continue only if this command reports status started for assignment ${item.assignment_id}, attempt ${item.attempt}.
If it denies the claim, reports an existing invocation, or fails, stop without performing the assignment.
Never substitute another ticket or attempt. The helper owns operational writes; do not write those files.

${workerPrompt(item)}

After writing your return, run exactly:
python scripts/fanout_dispatch.py finish --ticket ${shellArg(item.ticket_path)}
Report your operational receipt only after finish reports returned. If finish fails, report an
operational error rather than claiming completion. Include sha256 exactly from the finish receipt.`

const runWorker = item =>
  agent(continuous ? ticketPrompt(item) : workerPrompt(item), {
    label: item.assignment_id,
    phase: 'Workers',
    schema: {
      type: 'object',
      required: ['assignment_id', 'attempt', 'output_path', 'complete', 'summary', ...(continuous ? ['sha256'] : [])],
      properties: {
        assignment_id: { type: 'string' },
        attempt: { type: 'integer' },
        output_path: { type: 'string' },
        complete: { type: 'boolean' },
        summary: { type: 'string' },
        sha256: { type: 'string', pattern: '^[a-f0-9]{64}$' },
      },
      additionalProperties: false,
    },
    ...workerOptions,
  })

phase('Workers')
const results = Array(pending.length).fill(null)
const launched = []
let admissionStopped = false
const hostEvidence = Array(pending.length).fill(null)
if (continuous) {
  let next = 0
  let finished = 0
  // Slots are script functions. Every item still creates one fresh isolated agent.
  await parallel(Array.from({ length: Math.min(discovered.target, pending.length) }, () => async () => {
    while (!admissionStopped && next < pending.length) {
      const index = next++
      launched.push(pending[index].assignment_id)
      try {
        const receipt = await runWorker(pending[index])
        if (!receipt || receipt.assignment_id !== pending[index].assignment_id ||
            receipt.attempt !== pending[index].attempt || receipt.output_path !== pending[index].return_path ||
            receipt.complete !== true ||
            typeof receipt.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(receipt.sha256)) {
          admissionStopped = true
        } else {
          results[index] = receipt
          hostEvidence[index] = { ticket_id: pending[index].ticket_id, status: 'completed', evidence_sha256: receipt.sha256 }
        }
      } catch {
        admissionStopped = true
        log(`Worker ${pending[index].assignment_id}: host_error; no confirmed receipt`)
      }
      finished += 1
      log(`${finished}/${launched.length} admitted workers returned; ${pending.length - next} not yet admitted`)
    }
  }))
} else {
  const waveSize = concurrency === null ? 6 : concurrency
  for (let start = 0; start < pending.length; start += waveSize) {
    const wave = pending.slice(start, start + waveSize)
    launched.push(...wave.map(item => item.assignment_id))
    const waveResults = await parallel(wave.map(item => () => runWorker(item)))
    for (let index = 0; index < waveResults.length; index += 1) results[start + index] = waveResults[index]
    log(`wave ${Math.floor(start / waveSize) + 1}: ${waveResults.filter(Boolean).length}/${wave.length} workers returned`)
  }
}

phase('Verify')
const reconcilePrompt = continuous ? `First run:
python scripts/fanout_dispatch.py reconcile${runFlag}${ownerFlag}${admissionStopped ? ' --stop-admissions' : ''} --host-evidence - <<'ELARA_HOST_EVIDENCE'
${JSON.stringify(hostEvidence.filter(Boolean))}
ELARA_HOST_EVIDENCE
Only if reconciliation reports can_close true, run:
python scripts/fanout_dispatch.py close-session${runFlag}${ownerFlag}
If close refuses because invocations are unresolved, keep the session paused; never assert never_started
without positive host evidence, replay an unknown worker, or replace its token. Include the reconciliation
and close result as dispatch: {reconciliation: <exact reconcile JSON>, close: <exact close JSON or null>}
in your operational response, then run the status command below. Do not run checkpoint --passed;
only the parent may accept the scientific checkpoint and change the next session's target.
` : ''
const verification = await agent(
  `${reconcilePrompt}Run exactly:
python scripts/research_fanout.py status${fanoutFlag}
Report the resulting operational counts only (expected, complete, incomplete, missing, invalid,
exhausted, pending, and attempt_counts). Do not open returns and do not report findings. ${results.filter(Boolean).length} of
${launched.length} launched workers returned a receipt.`,
  {
    label: 'validate-operational-status',
    schema: {
      type: 'object',
      required: ['expected', 'complete', 'incomplete', 'missing', 'invalid', 'exhausted', 'pending', 'attempt_counts', ...(continuous ? ['dispatch'] : [])],
      properties: {
        expected: { type: 'integer' },
        complete: { type: 'integer' },
        incomplete: { type: 'integer' },
        missing: { type: 'integer' },
        invalid: { type: 'integer' },
        exhausted: { type: 'integer' },
        pending: { type: 'integer' },
        dispatch: {
          type: 'object', required: ['reconciliation', 'close'],
          properties: {
            reconciliation: { type: 'object', required: ['can_close'], properties: { can_close: { type: 'boolean' } } },
            close: { type: ['object', 'null'] },
          },
        },
        attempt_counts: {
          type: 'object',
          required: ['attempted', 'succeeded', 'failed', 'unusable', 'outstanding'],
          properties: {
            attempted: { type: 'integer' },
            succeeded: { type: 'integer' },
            failed: { type: 'integer' },
            unusable: { type: 'integer' },
            outstanding: { type: 'integer' },
          },
          additionalProperties: false,
        },
      },
      additionalProperties: true,
    },
    ...controllerOptions,
  },
)
if (!verification) throw new Error('Final verification failed; reconcile the existing session before resuming.')
if (continuous && (!verification.dispatch || !verification.dispatch.reconciliation ||
    typeof verification.dispatch.reconciliation.can_close !== 'boolean' ||
    (verification.dispatch.reconciliation.can_close && (!verification.dispatch.close ||
      verification.dispatch.close.state !== 'closed')))) {
  throw new Error('Dispatch finality was not verified; reconcile the existing session before resuming.')
}

return {
  fanout_dir: workflowArgs.fanout_dir,
  launched,
  admission_stopped: admissionStopped,
  returned: results.filter(Boolean).map(item => ({ assignment_id: item.assignment_id, attempt: item.attempt, complete: item.complete })),
  status: verification,
}
