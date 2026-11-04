export const meta = {
  name: 'elr-research-fanout',
  description: 'Run one bounded empirical-legal-research assignment (search, retrieval, cite-check, review) per isolated research worker',
  whenToUse:
    'ELARA research fan-outs under workflow/shared/observation-fanout.md, "Research fan-outs": Stage 02 query, author, citation-chain, and retrieval assignments; Stage 07 independent critics; Stage 19 claim-citation pairs; add-citations retrieval; fresh reviews. After scripts/research_fanout.py prepare has sealed a fan-out directory, run its pending assignments as restricted elr-research-worker subagents. Launched by the assistant as part of the stage; the researcher does not need to type it.',
  phases: [
    { title: 'Discover', detail: 'controller status: list the pending assignments and record their launches' },
    { title: 'Workers', detail: 'one fresh elr-research-worker per pending assignment, in a rolling pool' },
    { title: 'Verify', detail: 'controller status again: complete / incomplete / missing / exhausted' },
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
    throw new Error('Pass JSON arguments such as {"fanout_dir":"<prepared-fan-out-directory>"}.')
  }
}
if (typeof workflowArgs !== 'object' || workflowArgs === null ||
    typeof workflowArgs.fanout_dir !== 'string' || !workflowArgs.fanout_dir.trim()) {
  throw new Error('Pass { fanout_dir: "<prepared-fan-out-directory>" } (the directory scripts/research_fanout.py prepare sealed).')
}

// Two restricted worker types, both defined under .claude/agents/ so the platform enforces the
// tool surface: elr-worker (no web) runs the controller commands; elr-research-worker (web fetch
// and search, no browser, desktop, MCP, or user-prompt tools) performs the assignments.
// Optional model/effort passthrough applies to the research workers only.
const controllerOptions = { agentType: 'elr-worker' }
const workerOptions = { agentType: 'elr-research-worker' }
if (workflowArgs.model != null) workerOptions.model = workflowArgs.model
if (workflowArgs.effort != null) workerOptions.effort = workflowArgs.effort

const positiveInteger = (key, fallback, maximum) => {
  const value = workflowArgs[key]
  if (value == null) return fallback
  if (!Number.isInteger(value) || value < 1) throw new Error(`${key} must be a positive integer.`)
  return Math.min(value, maximum)
}
// The runtime runs at most 16 agents at once and 1,000 per run; Discover and Verify use two.
const concurrency = positiveInteger('concurrency', 6, 16)
const limit = positiveInteger('limit', 998, 998)
// Arguments of earlier versions (owner, capacity, resume_request, request_root,
// include_exhausted) are ignored.

const shellArg = value => "'" + String(value).replace(/'/g, "'\\''") + "'"
const fanoutFlag = ` --fanout-dir ${shellArg(workflowArgs.fanout_dir)}`

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
Run nothing else, open no brief or return, and do not retry. If it prints an error instead of
JSON, reply {"error": "<the first line of that error>"}.`,
    { label, schema, ...controllerOptions },
  )

const attemptCounts = {
  type: 'object',
  properties: {
    attempted: { type: 'integer' },
    succeeded: { type: 'integer' },
    failed: { type: 'integer' },
    unusable: { type: 'integer' },
    outstanding: { type: 'integer' },
  },
  additionalProperties: false,
}

phase('Discover')
let discovered
try {
  discovered = await controller(
    'discover-pending',
    `python scripts/research_fanout.py status${fanoutFlag} --record-launch --limit ${limit}`,
    {
      type: 'object',
      properties: {
        error: { type: 'string' },
        expected: { type: 'integer' },
        complete: { type: 'integer' },
        exhausted: { type: 'integer' },
        pending: { type: 'integer' },
        time_box_minutes: { type: 'integer' },
        launches_recorded: { type: 'integer' },
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
              attempts_so_far: { type: 'integer' },
            },
            additionalProperties: true,
          },
        },
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
const pending = []
const seen = new Set()
for (const item of discovered.pending_assignments) {
  if (!item || typeof item.assignment_id !== 'string' || !Number.isInteger(item.attempt) ||
      typeof item.brief_path !== 'string' || typeof item.return_path !== 'string') {
    throw new Error('The controller returned a malformed pending assignment; no worker was launched.')
  }
  if (!seen.has(item.assignment_id)) pending.push(item)
  seen.add(item.assignment_id)
}
if (pending.length > limit) throw new Error('The controller listed more assignments than the limit.')
const timeBox = Number.isInteger(discovered.time_box_minutes) ? discovered.time_box_minutes : 12
log(`${pending.length} pending assignment(s) to run, ${concurrency} at a time; ` +
  `${discovered.complete}/${discovered.expected} already complete; ${discovered.exhausted} exhausted`)

const workerPrompt = item => `Do ELARA research assignment ${item.assignment_id}; your rules are in your agent definition.
This is attempt ${item.attempt}.
1. Read your brief completely and follow it exactly: ${item.brief_path}
2. Write your return as UTF-8 JSON to this file and no other file: ${item.return_path}
   It must contain "assignment_id": "${item.assignment_id}", "attempt": ${item.attempt}, and a
   boolean "complete". Write it early with "complete": false, rewrite it after each completed
   step, and set "complete": true when the assignment is finished.
3. Time box: ${timeBox} minutes.
Reply with your assignment_id, attempt, the output path, whether the return is complete, and one
line of operational summary (counts, gaps, time), with no findings.`

const receiptSchema = {
  type: 'object',
  required: ['assignment_id', 'attempt', 'output_path', 'complete', 'summary'],
  properties: {
    assignment_id: { type: 'string' },
    attempt: { type: 'integer' },
    output_path: { type: 'string' },
    complete: { type: 'boolean' },
    summary: { type: 'string' },
  },
  additionalProperties: false,
}
const validReceipt = (receipt, item) =>
  Boolean(receipt) && receipt.assignment_id === item.assignment_id &&
  receipt.attempt === item.attempt && receipt.output_path === item.return_path &&
  typeof receipt.complete === 'boolean'

phase('Workers')
// A worker that fails or returns no receipt never stops the others. Its assignment is offered
// again, with its next sealed attempt, the next time this workflow runs.
const results = Array(pending.length).fill(null)
const noReceipt = []
const launched = []
let next = 0
let workerTypeMissing = false
await parallel(Array.from({ length: Math.min(concurrency, pending.length) }, () => async () => {
  while (!workerTypeMissing && next < pending.length) {
    const index = next++
    const item = pending[index]
    launched.push(item.assignment_id)
    let receipt = null
    try {
      receipt = await agent(workerPrompt(item), {
        label: item.assignment_id,
        phase: 'Workers',
        schema: receiptSchema,
        ...workerOptions,
      })
    } catch (error) {
      if (missingWorkerDefinitions(error)) workerTypeMissing = true
    }
    if (validReceipt(receipt, item)) results[index] = { assignment_id: item.assignment_id, attempt: item.attempt, complete: receipt.complete }
    else noReceipt.push(item.assignment_id)
    const done = results.filter(Boolean).length + noReceipt.length
    if (done % 10 === 0 || done === pending.length) {
      log(`${done}/${pending.length} workers finished; ${noReceipt.length} without a receipt`)
    }
  }
}))
if (workerTypeMissing) throw restartAdvice()

phase('Verify')
const verification = await controller(
  'validate-operational-status',
  `python scripts/research_fanout.py status${fanoutFlag}`,
  {
    type: 'object',
    properties: {
      error: { type: 'string' },
      expected: { type: 'integer' },
      complete: { type: 'integer' },
      incomplete: { type: 'integer' },
      missing: { type: 'integer' },
      invalid: { type: 'integer' },
      exhausted: { type: 'integer' },
      pending: { type: 'integer' },
      attempt_counts: attemptCounts,
    },
    additionalProperties: true,
  },
)
const status = {}
for (const key of ['expected', 'complete', 'incomplete', 'missing', 'invalid', 'exhausted', 'pending']) {
  if (verification && Number.isInteger(verification[key])) status[key] = verification[key]
}
if (verification && verification.attempt_counts && typeof verification.attempt_counts === 'object') {
  status.attempt_counts = verification.attempt_counts
}

return {
  fanout_dir: workflowArgs.fanout_dir,
  verified: Object.keys(status).length === 8,
  launched,
  returned: results.filter(Boolean).map(item => ({ assignment_id: item.assignment_id, attempt: item.attempt, complete: item.complete })),
  no_receipt: noReceipt,
  status,
}
