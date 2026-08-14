export const meta = {
  name: 'elr-observation-fanout',
  description: 'Run one frozen empirical-legal-research assignment per isolated subagent',
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

// Optional model/effort passthrough: when present in the parsed args they are added to
// every agent() call's options; when absent the options omit them entirely.
const agentOptions = {}
if (workflowArgs.model !== undefined && workflowArgs.model !== null) {
  agentOptions.model = workflowArgs.model
}
if (workflowArgs.effort !== undefined && workflowArgs.effort !== null) {
  agentOptions.effort = workflowArgs.effort
}

const blockRule = Number.isInteger(workflowArgs.block)
  ? `Read assignment files only to retain payload.block equal to ${workflowArgs.block}.`
  : 'Retain every pending assignment.'
const fixtureRule = workflowArgs.fixture === true
  ? 'This is an explicit kit validation fixture. Leave project state unchanged and apply the frozen fixture protocol.'
  : 'Confirm that project state routes to the active canonical fan-out stage before continuing.'

const discovered = await agent(
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

const receipts = await pipeline(discovered.assignments, assignmentPath =>
  agent(
    `Read workflow/shared/observation-fanout.md and then read exactly one assignment:
${assignmentPath}

Verify its frozen hashes. Do not inspect sibling assignments, worker returns, aggregates, or
ledgers. Perform only that assignment, write only its allowed worker-return path, and return an
operational receipt without the substantive label.`,
    {
      label: assignmentPath.split(/[\\/]/).pop(),
      schema: {
        type: 'object',
        required: ['assignment_id', 'unit_id', 'status', 'output_path'],
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
        },
        additionalProperties: false,
      },
      ...agentOptions,
    },
  ),
)

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

return verification
