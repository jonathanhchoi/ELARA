export const meta = {
  name: 'elr-research-fanout',
  description: 'Run one bounded empirical-legal-research assignment (search, retrieval, cite-check, review) per isolated research worker',
  whenToUse:
    'ELARA research fan-outs under workflow/shared/observation-fanout.md, "Research fan-outs": Stage 02 query, author, citation-chain, and retrieval waves; Stage 07 independent critics; Stage 19 claim-citation pairs; add-citations retrieval; fresh reviews. After scripts/research_fanout.py prepare has sealed a fan-out directory, run every pending assignment as one restricted elr-research-worker subagent. Launched by the assistant as part of the stage; the researcher does not need to type it.',
  phases: [
    { title: 'Discover', detail: 'controller status: pending assignments, launches recorded' },
    { title: 'Workers', detail: 'one elr-research-worker per pending assignment, in bounded waves' },
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

// Bounded waves with a barrier between them: research workers usually share rate-limited APIs and
// indexes, so the default ceiling is six at once (workflow/shared/guardrails.md section 7). Pass
// `concurrency` to change it; the workflow runtime's own cap still applies above it.
const concurrency = Number.isInteger(workflowArgs.concurrency) && workflowArgs.concurrency > 0
  ? workflowArgs.concurrency
  : 6
const limitFlag = Number.isInteger(workflowArgs.limit) && workflowArgs.limit > 0
  ? ` --limit ${workflowArgs.limit}`
  : ''
const exhaustedFlag = workflowArgs.include_exhausted === true ? ' --include-exhausted' : ''

phase('Discover')
const discovered = await agent(
  `Read workflow/shared/observation-fanout.md (the section "Research fan-outs"). Run exactly:
python scripts/research_fanout.py status --fanout-dir "${workflowArgs.fanout_dir}" --include-pending --record-launch${limitFlag}${exhaustedFlag}
Return the pending_assignments array from its output (assignment_id, brief_path, return_path) and the
counts. Do not open briefs or returns and do not report findings.`,
  {
    label: 'discover-pending',
    schema: {
      type: 'object',
      required: ['pending_assignments', 'expected', 'complete', 'exhausted', 'time_box_minutes'],
      properties: {
        pending_assignments: {
          type: 'array',
          items: {
            type: 'object',
            required: ['assignment_id', 'brief_path', 'return_path'],
            properties: {
              assignment_id: { type: 'string' },
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
const pending = discovered.pending_assignments
log(`${pending.length} pending assignment(s); ${discovered.complete}/${discovered.expected} already complete; ${discovered.exhausted} exhausted`)

const workerPrompt = item => `You are one ELARA research worker under workflow/shared/observation-fanout.md. Do exactly one
assignment and nothing else.

1. Read your brief completely: ${item.brief_path}
   It contains the frozen instructions for this unit, the return schema, and the rules. Follow it exactly.
2. Write your structured return as UTF-8 JSON to this path and no other:
   ${item.return_path}
   The return must be a JSON object with "assignment_id": "${item.assignment_id}" and a boolean "complete".
   Write it early with "complete": false, rewrite it after each completed step or route, and rewrite it a
   last time with "complete": true when the assignment is finished. Never write any other file.
3. Time box: ${discovered.time_box_minutes} minutes. Every network call carries a hard timeout; never
   sleep, poll, or wait more than about 30 seconds in total.
4. A 401/403/429, CAPTCHA, "verifying you are human" page, or login wall is a typed access gap
   (record url, status or message, UTC time) — move on; at most one retry for a 429; never spoof or
   escalate to another surface. You have no browser, computer-use, desktop, or MCP tools; do not try.
5. Do not read sibling briefs or returns, ledgers, aggregates, or project state. Record only what you
   actually retrieved; never invent or complete a citation, quotation, count, or URL.

Reply with your assignment_id, the output path, whether the return is complete, and one line of
operational summary (counts, gaps, time) — no findings.`

const runWorker = item =>
  agent(workerPrompt(item), {
    label: item.assignment_id,
    phase: 'Workers',
    schema: {
      type: 'object',
      required: ['assignment_id', 'output_path', 'complete', 'summary'],
      properties: {
        assignment_id: { type: 'string' },
        output_path: { type: 'string' },
        complete: { type: 'boolean' },
        summary: { type: 'string' },
      },
      additionalProperties: false,
    },
    ...workerOptions,
  })

phase('Workers')
const results = []
for (let start = 0; start < pending.length; start += concurrency) {
  const wave = pending.slice(start, start + concurrency)
  const waveResults = await parallel(wave.map(item => () => runWorker(item)))
  results.push(...waveResults)
  log(`wave ${Math.floor(start / concurrency) + 1}: ${waveResults.filter(Boolean).length}/${wave.length} workers returned`)
}

phase('Verify')
const verification = await agent(
  `Run exactly:
python scripts/research_fanout.py status --fanout-dir "${workflowArgs.fanout_dir}"
Report the resulting operational counts only (expected, complete, incomplete, missing, invalid,
exhausted, pending). Do not open returns and do not report findings. ${results.filter(Boolean).length} of
${pending.length} launched workers returned a receipt.`,
  {
    label: 'validate-operational-status',
    schema: {
      type: 'object',
      required: ['expected', 'complete', 'incomplete', 'missing', 'invalid', 'exhausted', 'pending'],
      properties: {
        expected: { type: 'integer' },
        complete: { type: 'integer' },
        incomplete: { type: 'integer' },
        missing: { type: 'integer' },
        invalid: { type: 'integer' },
        exhausted: { type: 'integer' },
        pending: { type: 'integer' },
      },
      additionalProperties: false,
    },
    ...controllerOptions,
  },
)

return {
  fanout_dir: workflowArgs.fanout_dir,
  launched: pending.map(item => item.assignment_id),
  returned: results.filter(Boolean).map(item => ({ assignment_id: item.assignment_id, complete: item.complete })),
  status: verification,
}
