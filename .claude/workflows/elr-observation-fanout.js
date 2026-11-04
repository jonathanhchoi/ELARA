export const meta = {
  name: 'elr-observation-fanout',
  description: 'Run one frozen empirical-legal-research coding or audit assignment per isolated subagent',
  whenToUse:
    'ELARA Stages 08, 11, 12, and 15: after scripts/unit_fanout.py prepare has sealed a run directory, run its pending assignments as restricted elr-worker subagents and report operational counts. Launched by the assistant as part of the stage; the researcher does not need to type it.',
  phases: [
    { title: 'Discover', detail: 'controller status: list the pending assignments and record their launches' },
    { title: 'Workers', detail: 'one fresh elr-worker per pending assignment, in a rolling pool' },
    { title: 'Verify', detail: 'controller status again: operational counts only' },
  ],
}

// Accept the Workflow-tool `args` global when it is defined and non-null; otherwise fall
// back to a `workflowArgs` global provided by a saved-workflow host.
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
if (typeof workflowArgs !== 'object' || workflowArgs === null ||
    typeof workflowArgs.run_dir !== 'string' || !workflowArgs.run_dir.trim()) {
  throw new Error('Pass { run_dir: "<allocated-run-directory>" }.')
}

// Every agent runs as the kit's restricted worker type (.claude/agents/elr-worker.md), so the
// platform, not the prompt, removes web, interactive, browser, desktop, and MCP tools.
const agentOptions = { agentType: 'elr-worker' }
if (workflowArgs.model != null) agentOptions.model = workflowArgs.model
if (workflowArgs.effort != null) agentOptions.effort = workflowArgs.effort

const positiveInteger = (key, fallback, maximum) => {
  const value = workflowArgs[key]
  if (value == null) return fallback
  if (!Number.isInteger(value) || value < 1) throw new Error(`${key} must be a positive integer.`)
  return Math.min(value, maximum)
}
// The runtime runs at most 16 agents at once and 1,000 per run; Discover and Verify use two.
const concurrency = positiveInteger('concurrency', 6, 16)
const limit = positiveInteger('limit', 998, 998)
if (workflowArgs.block != null && !Number.isInteger(workflowArgs.block)) {
  throw new Error('block must be an integer.')
}
// Arguments of earlier versions (owner, capacity, resume_request, request_root, fixture) are ignored.

const shellArg = value => "'" + String(value).replace(/'/g, "'\\''") + "'"
const runFlag = ` --run-dir ${shellArg(workflowArgs.run_dir)}`
const blockFlag = workflowArgs.block == null ? '' : ` --block ${workflowArgs.block}`

// Claude Code loads .claude/agents/ when it starts in the project folder. Translate a missing
// worker type into the one instruction the researcher needs.
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

const controller = (label, command, schema) =>
  agent(
    `Run this one command exactly as written and reply with the JSON it prints:
${command}
Run nothing else, read no other file, and do not retry. If it prints an error instead of JSON,
reply {"error": "<the first line of that error>"}.`,
    { label, schema, ...agentOptions },
  )

phase('Discover')
const pendingItem = {
  type: 'object',
  required: ['assignment_id', 'unit_id', 'assignment_path', 'return_path', 'draft_path'],
  properties: {
    assignment_id: { type: 'string' },
    unit_id: { type: 'string' },
    attempt: { type: 'integer' },
    assignment_path: { type: 'string' },
    return_path: { type: 'string' },
    draft_path: { type: 'string' },
    launches: { type: 'integer' },
  },
  additionalProperties: true,
}
let discovered
try {
  discovered = await controller(
    'discover-pending',
    `python scripts/unit_fanout.py status${runFlag} --record-launch --limit ${limit}${blockFlag}`,
    {
      type: 'object',
      properties: {
        error: { type: 'string' },
        expected: { type: 'integer' },
        terminal: { type: 'integer' },
        pending: { type: 'integer' },
        launches_recorded: { type: 'integer' },
        closed_after_launches: { type: 'array', items: { type: 'string' } },
        pending_assignments: { type: 'array', items: pendingItem },
      },
      additionalProperties: true,
    },
  )
} catch (error) {
  if (missingWorkerDefinitions(error)) throw restartAdvice()
  throw error
}
if (!discovered || typeof discovered.error === 'string' || !Array.isArray(discovered.pending_assignments)) {
  throw new Error(
    'The controller did not list the pending assignments, so no worker was launched' +
    (discovered && typeof discovered.error === 'string' ? ` (${discovered.error})` : '') +
    '. Follow "When something breaks" in workflow/shared/operational-recovery.md.',
  )
}
const items = []
const seen = new Set()
for (const item of discovered.pending_assignments) {
  if (!item || typeof item.assignment_id !== 'string' || typeof item.assignment_path !== 'string' ||
      typeof item.return_path !== 'string' || typeof item.draft_path !== 'string') {
    throw new Error('The controller returned a malformed pending assignment; no worker was launched.')
  }
  if (!seen.has(item.assignment_id)) items.push(item)
  seen.add(item.assignment_id)
}
if (items.length > limit) throw new Error('The controller listed more assignments than the limit.')
log(`${items.length} pending assignment(s) to run, ${concurrency} at a time`)

const workerPrompt = item => `Do ELARA assignment ${item.assignment_id}; your rules are in your agent definition.
1. Read your assignment file: ${item.assignment_path}
2. Do exactly what it says. Write your return envelope as JSON with the Write tool to this
   draft file and no other file: ${item.draft_path}
3. Submit it by running:
python scripts/unit_fanout.py submit${runFlag} --assignment-id ${shellArg(item.assignment_id)} --input ${shellArg(item.draft_path)}
4. Reply with the JSON receipt that command prints.`

const terminalStatuses = [
  'succeeded', 'schema_failed', 'quote_failed', 'refused', 'unreadable', 'wrong_document',
  'exhausted_retry', 'worker_error', 'already_submitted',
]
const receiptSchema = {
  type: 'object',
  required: ['assignment_id', 'unit_id', 'status', 'output_path', 'sha256'],
  properties: {
    assignment_id: { type: 'string' },
    unit_id: { type: 'string' },
    status: { type: 'string', enum: terminalStatuses },
    output_path: { type: 'string' },
    sha256: { type: 'string' },
  },
  additionalProperties: false,
}
const validReceipt = (receipt, item) =>
  Boolean(receipt) && receipt.assignment_id === item.assignment_id &&
  receipt.output_path === item.return_path && terminalStatuses.includes(receipt.status) &&
  typeof receipt.sha256 === 'string' && /^[a-f0-9]{64}$/.test(receipt.sha256)

phase('Workers')
// A worker that fails or returns no receipt never stops the others: its assignment stays
// pending on disk, and the controller closes it as worker_error after its second launch.
const receipts = Array(items.length).fill(null)
const noReceipt = []
let next = 0
let finished = 0
let workerTypeMissing = false
await parallel(Array.from({ length: Math.min(concurrency, items.length) }, () => async () => {
  while (!workerTypeMissing && next < items.length) {
    const index = next++
    const item = items[index]
    let receipt = null
    try {
      receipt = await agent(workerPrompt(item), {
        label: item.assignment_id,
        phase: 'Workers',
        schema: receiptSchema,
        ...agentOptions,
      })
    } catch (error) {
      if (missingWorkerDefinitions(error)) workerTypeMissing = true
    }
    if (validReceipt(receipt, item)) receipts[index] = receipt
    else noReceipt.push(item.assignment_id)
    finished += 1
    if (finished % 10 === 0 || finished === items.length) {
      log(`${finished}/${items.length} workers finished; ${noReceipt.length} without a receipt`)
    }
  }
}))
if (workerTypeMissing) throw restartAdvice()

phase('Verify')
const verification = await controller(
  'validate-operational-status',
  `python scripts/unit_fanout.py status${runFlag}`,
  {
    type: 'object',
    properties: {
      error: { type: 'string' },
      expected: { type: 'integer' },
      terminal: { type: 'integer' },
      invalid: { type: 'integer' },
      pending: { type: 'integer' },
    },
    additionalProperties: true,
  },
)
const counts = {}
for (const key of ['expected', 'terminal', 'invalid', 'pending']) {
  if (verification && Number.isInteger(verification[key])) counts[key] = verification[key]
}

return {
  ...counts,
  verified: Object.keys(counts).length === 4,
  launched: finished,
  receipts: receipts.filter(Boolean).length,
  no_receipt: noReceipt,
  closed_after_launches: Array.isArray(discovered.closed_after_launches) ? discovered.closed_after_launches : [],
}
