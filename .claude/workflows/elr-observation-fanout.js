export const meta = {
  name: 'elr-observation-fanout',
  description: 'Run one frozen empirical-legal-research coding or audit assignment per isolated subagent',
  whenToUse:
    'ELARA Stages 08, 11, 12, and 15: after scripts/unit_fanout.py prepare has sealed a run directory, run every pending assignment as one restricted elr-worker subagent and report operational counts. Launched by the assistant as part of the stage; the researcher does not need to type it.',
  phases: [
    { title: 'Discover', detail: 'controller status: which assignments are still pending' },
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

// Optional `concurrency`: when set to a positive integer, workers run in bounded waves of that size
// with a barrier between waves (for a shared, rate-limited model route). When absent, pipeline() runs
// under the workflow runtime's own concurrency cap, which is the host-managed default.
const concurrency = Number.isInteger(workflowArgs.concurrency) && workflowArgs.concurrency > 0
  ? workflowArgs.concurrency
  : null

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
    `Read AGENTS.md and workflow/shared/observation-fanout.md completely. Run:
python scripts/unit_fanout.py status --run-dir "${workflowArgs.run_dir}" --include-pending
${fixtureRule} ${blockRule} Return the selected pending assignment paths only. Do not
read worker-return contents or report substantive labels.`,
    {
      label: 'discover-pending',
      schema: {
        type: 'object',
        required: ['assignments'],
        properties: {
          assignments: { type: 'array', items: { type: 'string' } },
        },
        additionalProperties: false,
      },
      ...agentOptions,
    },
  )
} catch (error) {
  if (missingWorkerDefinitions(error)) throw restartAdvice()
  throw error
}
log(`${discovered.assignments.length} pending assignment(s) to run`)

const workerPrompt = assignmentPath => `Read workflow/shared/observation-fanout.md and then read exactly one assignment:
${assignmentPath}

Verify its frozen hashes. Do not inspect sibling assignments, worker returns, aggregates, or
ledgers. Perform only that assignment. Construct the return envelope in memory and submit it on
standard input with:
python scripts/unit_fanout.py submit --run-dir "${workflowArgs.run_dir}" --assignment-id "<assignment_id from the assignment>"
Do not write the worker-return path directly. Return the command's operational receipt without the
substantive label.`

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

const runWorker = assignmentPath =>
  agent(workerPrompt(assignmentPath), {
    label: assignmentPath.split(/[\\/]/).pop(),
    phase: 'Workers',
    schema: receiptSchema,
    ...agentOptions,
  })

phase('Workers')
let receipts = []
if (concurrency === null) {
  receipts = await pipeline(discovered.assignments, runWorker)
} else {
  for (let start = 0; start < discovered.assignments.length; start += concurrency) {
    const wave = discovered.assignments.slice(start, start + concurrency)
    const waveReceipts = await parallel(wave.map(assignmentPath => () => runWorker(assignmentPath)))
    receipts.push(...waveReceipts)
    log(`wave ${Math.floor(start / concurrency) + 1}: ${waveReceipts.filter(Boolean).length}/${wave.length} receipts`)
  }
}

phase('Verify')
const verification = await agent(
  `Read workflow/shared/observation-fanout.md. Run:
python scripts/unit_fanout.py status --run-dir "${workflowArgs.run_dir}"
Report the resulting operational counts only. Do not edit a shared ledger, report label frequencies,
or expose other substantive outcomes. There were ${receipts.filter(Boolean).length} worker receipts.`,
  {
    label: 'validate-operational-status',
    schema: {
      type: 'object',
      required: ['expected', 'terminal', 'invalid', 'pending'],
      properties: {
        expected: { type: 'integer' },
        terminal: { type: 'integer' },
        invalid: { type: 'integer' },
        pending: { type: 'integer' },
      },
      additionalProperties: false,
    },
    ...agentOptions,
  },
)

return {
  launched: discovered.assignments.length,
  receipts: receipts.filter(Boolean).length,
  ...verification,
}
