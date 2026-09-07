export const meta = {
  name: 'elr-observation-fanout',
  description: 'Run one frozen empirical-legal-research coding or audit assignment per isolated subagent',
  whenToUse:
    'ELARA Stages 08, 11, 12, and 15: after scripts/unit_fanout.py prepare has sealed a run directory, run the approved pending assignments as restricted elr-worker subagents and report operational counts. Launched by the assistant as part of the stage; the researcher does not need to type it.',
  phases: [
    { title: 'Discover', detail: 'controller dispatch: reserve the approved pending assignments' },
    { title: 'Workers', detail: 'one elr-worker per pending assignment; each submits through the controller' },
    { title: 'Verify', detail: 'controller status again: operational counts only' },
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
    throw new Error('Pass JSON arguments such as {"run_dir":"<allocated-run-directory>"}.')
  }
}
if (typeof workflowArgs !== 'object' || workflowArgs === null || typeof workflowArgs.run_dir !== 'string') {
  throw new Error('Pass { run_dir: "<allocated-run-directory>" }.')
}

// Every agent in this workflow runs as the kit's restricted worker type (`.claude/agents/elr-worker.md`:
// Read/Bash/Glob/Grep only; no web, no interactive, browser, desktop, or MCP tools). The tool surface is
// then enforced by the platform rather than by prompt — see workflow/shared/observation-fanout.md,
// "Worker tool surface, time boxes, and crash-resume". Optional model/effort passthrough: when present
// in the parsed args they are added to every agent() call's options; when absent the options omit them.
const agentOptions = { agentType: 'elr-worker' }
if (workflowArgs.model !== undefined && workflowArgs.model !== null) {
  agentOptions.model = workflowArgs.model
}
if (workflowArgs.effort !== undefined && workflowArgs.effort !== null) {
  agentOptions.effort = workflowArgs.effort
}

// A continuous session holds its recorded target through this accepted batch. Explicit concurrency
// fixes that target. Unmigrated runs retain their original wave/pipeline scheduling below.
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
// The runtime allows 1,000 agents in a workflow; Discover and Verify consume two of them.
const limit = Math.min(workflowArgs.limit == null ? 998 : workflowArgs.limit, 998)
const shellArg = value => "'" + String(value).replace(/'/g, "'\\''") + "'"
const runFlag = ` --run-dir ${shellArg(workflowArgs.run_dir)}`
const ownerFlag = workflowArgs.owner == null ? '' : ` --owner ${shellArg(workflowArgs.owner)}`
for (const key of ['resume_request', 'request_root']) {
  if (workflowArgs[key] != null && (typeof workflowArgs[key] !== 'string' || !workflowArgs[key].trim())) {
    throw new Error(`${key} must be a nonempty path.`)
  }
}
const resumeFlags = (workflowArgs.resume_request == null ? '' : ` --request ${shellArg(workflowArgs.resume_request)}`) +
  (workflowArgs.request_root == null ? '' : ` --request-root ${shellArg(workflowArgs.request_root)}`)
const dispatchFlags = `${runFlag} --kind coding --host claude --capacity ${capacity} --limit ${limit}` +
  ownerFlag + resumeFlags + (concurrency === null ? '' : ` --concurrency ${concurrency}`) +
  (Number.isInteger(workflowArgs.block) ? ` --block ${workflowArgs.block}` : '')

const blockRule = Number.isInteger(workflowArgs.block)
  ? `Read assignment files only to retain payload.block equal to ${workflowArgs.block}.`
  : 'Retain every pending assignment.'
const fixtureRule = workflowArgs.fixture === true
  ? 'This is an explicit kit validation fixture. Leave project state unchanged and apply the frozen fixture protocol.'
  : 'Confirm that project state routes to the active canonical fan-out stage before continuing.'

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
    `Read AGENTS.md and workflow/shared/observation-fanout.md completely. ${fixtureRule}
Run the following command exactly ONCE, copying every identifier literally. Do not retry or correct
an already issued command; if it fails or differs from the requested command, report discovery failure.
python scripts/fanout_dispatch.py open-session${dispatchFlags}
Return its operational JSON unchanged when mode is continuous. The owner must be the stable identifier
provided by the parent; never invent an owner, migrate a legacy run, or override an active session.
If and only if it reports mode legacy, run:
python scripts/unit_fanout.py status${runFlag} --include-pending
${blockRule} Return {"mode":"legacy","assignments":[the selected pending assignment paths]},
limited to the first ${limit} selected paths in controller order. Do not read worker-return contents or
report substantive labels. On any command error return only
{"mode":"failed","status":"discovery_failure","error":"dispatch_failed_closed"}.
A command error never permits the legacy route; do not include raw error payloads.`,
    {
      label: 'discover-pending',
      schema: {
        type: 'object',
        required: ['mode'],
        properties: {
          mode: { type: 'string', enum: ['continuous', 'legacy', 'failed'] },
          assignments: { type: 'array', items: { type: 'string' } },
          tickets: { type: 'array', items: { type: 'object' } },
          target: { type: 'integer' },
        },
        additionalProperties: true,
      },
      ...agentOptions,
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
const items = continuous ? discovered.tickets : discovered.assignments
if (!Array.isArray(items) || items.length > limit) throw new Error('Invalid or oversized dispatch batch.')
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
for (const item of items) {
  const key = continuous ? item && item.ticket_id : item
  if (typeof key !== 'string' || seen.has(key) || (continuous &&
      (typeof item.ticket_path !== 'string' || typeof item.assignment_path !== 'string' ||
       typeof item.assignment_id !== 'string' || typeof item.unit_id !== 'string' ||
       typeof item.return_path !== 'string' || seenAssignments.has(item.assignment_id)))) {
    throw new Error('Invalid or duplicate dispatch item.')
  }
  seen.add(key)
  if (continuous) seenAssignments.add(item.assignment_id)
}
log(`${items.length} pending assignment(s) to run`)

const workerPrompt = assignmentPath => `Read workflow/shared/observation-fanout.md and then read exactly one assignment:
${assignmentPath}

Verify its frozen hashes. Do not inspect sibling assignments, worker returns, aggregates, or
ledgers. Perform only that assignment. Construct the return envelope in memory and submit it on
standard input with:
python scripts/unit_fanout.py submit${runFlag} --assignment-id "<assignment_id from the assignment>"
Do not write the worker-return path directly. Return the command's operational receipt without the
substantive label.`

const ticketPrompt = item => `Your FIRST operation, before reading any assignment or source, must be:
python scripts/fanout_dispatch.py start --ticket ${shellArg(item.ticket_path)}
Continue only if this command reports status started for assignment ${item.assignment_id}. If it denies
the claim, reports an existing invocation, or fails, stop without reading or coding the assignment.
Never substitute another ticket or attempt. The helper owns operational writes; do not write those files.

${workerPrompt(item.assignment_path)}

After submission, run exactly:
python scripts/fanout_dispatch.py finish --ticket ${shellArg(item.ticket_path)}
Return the original unit_fanout submit receipt only after finish reports returned. If finish fails,
report an operational error instead of claiming completion.`

const receiptSchema = {
  type: 'object',
  required: ['assignment_id', 'unit_id', 'status', 'output_path', 'sha256'],
  properties: {
    assignment_id: { type: 'string' },
    unit_id: { type: 'string' },
    status: {
      type: 'string',
      enum: [
        'succeeded',
        'schema_failed',
        'quote_failed',
        'refused',
        'unreadable',
        'wrong_document',
        'exhausted_retry',
        'worker_error',
        'invalid',
      ],
    },
    output_path: { type: 'string' },
    sha256: { type: 'string' },
  },
  additionalProperties: false,
}

const runWorker = item =>
  agent(continuous ? ticketPrompt(item) : workerPrompt(item), {
    label: continuous ? item.assignment_id : item.split(/[\\/]/).pop(),
    phase: 'Workers',
    schema: receiptSchema,
    ...agentOptions,
  })

phase('Workers')
let receipts = []
let launched = 0
let admissionStopped = false
const hostEvidence = Array(items.length).fill(null)
if (continuous) {
  receipts = Array(items.length).fill(null)
  let next = 0
  let finished = 0
  // These are asynchronous script slots, not reusable agents. Claim the next index before awaiting
  // so launches retain manifest order while every free slot immediately admits a fresh worker.
  await parallel(Array.from({ length: Math.min(discovered.target, items.length) }, () => async () => {
    while (!admissionStopped && next < items.length) {
      const index = next++
      launched += 1
      try {
        const receipt = await runWorker(items[index])
        if (!receipt || receipt.assignment_id !== items[index].assignment_id ||
            receipt.unit_id !== items[index].unit_id || receipt.output_path !== items[index].return_path ||
            !receiptSchema.properties.status.enum.includes(receipt.status) || receipt.status === 'invalid' ||
            typeof receipt.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(receipt.sha256)) {
          admissionStopped = true
        } else {
          receipts[index] = receipt
          hostEvidence[index] = { ticket_id: items[index].ticket_id, status: 'completed', evidence_sha256: receipt.sha256 }
        }
      } catch {
        admissionStopped = true
        log(`Worker ${items[index].assignment_id}: host_error; no confirmed receipt`)
      }
      finished += 1
      log(`${finished}/${launched} admitted workers returned; ${items.length - next} not yet admitted`)
    }
  }))
} else if (concurrency === null) {
  launched = items.length
  receipts = await pipeline(items, runWorker)
} else {
  for (let start = 0; start < items.length; start += concurrency) {
    const wave = items.slice(start, start + concurrency)
    launched += wave.length
    const waveReceipts = await parallel(wave.map(assignmentPath => () => runWorker(assignmentPath)))
    receipts.push(...waveReceipts)
    log(`wave ${Math.floor(start / concurrency) + 1}: ${waveReceipts.filter(Boolean).length}/${wave.length} receipts`)
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
  `Read workflow/shared/observation-fanout.md. ${reconcilePrompt}Run:
python scripts/unit_fanout.py status${runFlag}
Report the resulting operational counts only. Do not edit a shared ledger, report label frequencies,
or expose other substantive outcomes. There were ${receipts.filter(Boolean).length} worker receipts.`,
  {
    label: 'validate-operational-status',
    schema: {
      type: 'object',
      required: ['expected', 'terminal', 'invalid', 'pending', ...(continuous ? ['dispatch'] : [])],
      properties: {
        expected: { type: 'integer' },
        terminal: { type: 'integer' },
        invalid: { type: 'integer' },
        pending: { type: 'integer' },
        dispatch: {
          type: 'object', required: ['reconciliation', 'close'],
          properties: {
            reconciliation: { type: 'object', required: ['can_close'], properties: { can_close: { type: 'boolean' } } },
            close: { type: ['object', 'null'] },
          },
        },
      },
      additionalProperties: true,
    },
    ...agentOptions,
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
  ...verification,
  launched,
  receipts: receipts.filter(Boolean).length,
  admission_stopped: admissionStopped,
}
