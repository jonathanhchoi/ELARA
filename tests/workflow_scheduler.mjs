// Execute the saved workflow bodies against a controlled host. No model calls or wall-clock sleeps.
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = process.argv[2] || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const flush = () => new Promise(resolve => setImmediate(resolve))
const sources = new Map()

function item(index) {
  return {
    ticket_id: `ticket-${index}`, ticket_path: `/fixture/tickets/${index}.json`,
    assignment_id: `assignment-${index}`, unit_id: `unit-${index}`, attempt: 1,
    assignment_path: `/fixture/assignments/${index}.json`,
    brief_path: `/fixture/briefs/${index}.md`, return_path: `/fixture/returns/${index}.json`,
  }
}

async function host(kind, { count = 18, target = 6, mode = 'continuous', args = {}, discovery = {}, verification = {}, nativeExtraStrings = false } = {}) {
  const file = `.claude/workflows/elr-${kind === 'coding' ? 'observation' : 'research'}-fanout.js`
  if (!sources.has(file)) sources.set(file, readFile(path.join(root, file), 'utf8'))
  const source = (await sources.get(file)).replace('export const meta =', 'const meta =')
  const items = Array.from({ length: count }, (_, index) => item(index))
  const discovered = {
    mode, target, owner: args.owner ?? 'native-session-fixture', state: 'active', reused_session: false, tickets: items, assignments: items.map(row => row.assignment_path),
    pending_assignments: items, expected: count, complete: 0, exhausted: 0, time_box_minutes: 5,
    ...discovery,
  }
  const config = {
    ...(kind === 'coding' ? { run_dir: '/fixture' } : { fanout_dir: '/fixture' }),
    ...(mode === 'continuous' ? { owner: 'native-session-fixture', capacity: Math.max(6, target) } : {}),
    ...args,
  }
  const calls = [], logs = [], starts = [], finishes = [], waiting = new Map()
  let active = 0, peak = 0, done = false, outcome, failure, verifyPrompt
  // The installed native StructuredOutput tool can stringify undeclared extra properties.
  // Control fields must therefore be explicitly typed rather than relying on additionalProperties.
  const structured = (value, schema) => {
    if (!nativeExtraStrings || value === null) return value
    if (Array.isArray(value)) return value.map(entry => structured(entry, schema.items || {}))
    if (typeof value !== 'object') return value
    return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key,
      schema.properties?.[key] ? structured(entry, schema.properties[key])
        : typeof entry === 'string' ? entry : JSON.stringify(entry)]))
  }
  const agent = async (prompt, options) => {
    calls.push({ prompt, options })
    assert.ok(calls.length <= 1000, 'workflow exceeded its total agent budget')
    if (options.phase !== 'Workers') {
      assert.equal(active, 0, 'controller verification overlapped unfinished workers')
      if (options.label === 'discover-pending') return structured(discovered, options.schema)
      verifyPrompt = prompt
      const status = kind === 'coding'
        ? { expected: count, terminal: finishes.length, invalid: 0, pending: count - finishes.length }
        : { expected: count, complete: finishes.length, incomplete: 0, missing: count - finishes.length,
            invalid: 0, exhausted: 0, pending: count - finishes.length,
            attempt_counts: { attempted: starts.length, succeeded: finishes.length, failed: 0,
              unusable: 0, outstanding: count - finishes.length } }
      if (mode === 'continuous') {
        const canClose = !prompt.includes('--stop-admissions')
        status.dispatch = { reconciliation: { can_close: canClose }, close: canClose ? { state: 'closed' } : null }
        const evidence = JSON.parse(prompt.split("<<'ELARA_HOST_EVIDENCE'\n")[1].split('\nELARA_HOST_EVIDENCE')[0])
        for (const row of evidence) {
          const index = Number(row.ticket_id.replace('ticket-', ''))
          assert.ok(finishes.includes(index), 'host declared completion before worker returned')
          assert.equal(row.status, 'completed')
          assert.match(row.evidence_sha256, /^[a-f0-9]{64}$/)
        }
        assert.deepEqual(evidence.map(row => Number(row.ticket_id.replace('ticket-', ''))),
          evidence.map(row => Number(row.ticket_id.replace('ticket-', ''))).sort((a, b) => a - b))
      }
      return structured({ ...status, ...verification }, options.schema)
    }
    const index = mode === 'continuous' || kind === 'research'
      ? Number(options.label.replace('assignment-', '')) : Number(options.label.replace('.json', ''))
    assert.ok(!waiting.has(index) && !starts.includes(index), 'assignment dispatched more than once')
    starts.push(index)
    active += 1
    peak = Math.max(peak, active)
    return new Promise((resolve, reject) => waiting.set(index, {
      resolve: value => { active -= 1; finishes.push(index); waiting.delete(index); resolve(value) },
      reject: error => { active -= 1; finishes.push(index); waiting.delete(index); reject(error) },
    }))
  }
  // Anthropic's documented parallel primitive settles every thunk; it does not reject a whole batch.
  const parallel = async thunks => (await Promise.allSettled(thunks.map(fn => fn())))
    .map(result => result.status === 'fulfilled' ? result.value : null)
  const pipeline = async (rows, ...stages) => parallel(rows.map((row, index) => async () => {
    let result = row
    for (const stage of stages) {
      if (result === null) break
      result = await stage(result, row, index)
    }
    return result
  }))
  const execute = new AsyncFunction('args', 'agent', 'parallel', 'pipeline', 'phase', 'log', source)
  execute(config, agent, parallel, pipeline, () => {}, message => logs.push(message))
    .then(value => { outcome = value; done = true }, error => { failure = error; done = true })
  await flush()
  const receipt = index => kind === 'coding'
    ? { assignment_id: items[index].assignment_id, unit_id: `unit-${index}`, status: 'succeeded',
        output_path: items[index].return_path, sha256: 'a'.repeat(64) }
    : { assignment_id: items[index].assignment_id, attempt: 1, output_path: items[index].return_path,
        complete: true, summary: 'one completed assignment', sha256: 'a'.repeat(64) }
  return {
    calls, logs, starts, finishes, waiting, config,
    get peak() { return peak }, get done() { return done }, get result() { return outcome },
    get failure() { return failure }, get verifyPrompt() { return verifyPrompt },
    async finish(index, replacement) {
      assert.ok(waiting.has(index), `worker ${index} was not running`)
      waiting.get(index).resolve(replacement === undefined ? receipt(index) : replacement)
      await flush()
    },
    async reject(index) {
      waiting.get(index).reject(new Error('SECRET_SUBSTANTIVE_LABEL_IN_PROVIDER_ERROR 429 Retry-After: 60'))
      await flush()
    },
    async drain() {
      for (let guard = 0; !done && guard < count + 10; guard += 1) {
        for (const index of [...waiting.keys()]) waiting.get(index).resolve(receipt(index))
        await flush()
      }
      assert.ok(done, 'workflow did not settle')
      if (failure) throw failure
      return outcome
    },
  }
}

let passed = 0
async function test(name, run) {
  await run()
  passed += 1
  process.stdout.write(`ok ${passed} - ${name}\n`)
}

for (const kind of ['coding', 'research']) {
  await test(`${kind}: rolling queue refills before the slow first worker`, async () => {
    const h = await host(kind)
    assert.deepEqual(h.starts, [0, 1, 2, 3, 4, 5])
    await h.finish(1)
    assert.ok(h.waiting.has(0))
    assert.ok(h.starts.includes(6), 'seventh worker waited for the first wave')
    const result = await h.drain()
    assert.equal(h.peak, 6)
    assert.deepEqual(h.starts, Array.from({ length: 18 }, (_, i) => i))
    assert.equal(h.calls.length, 20)
    assert.equal(result.admission_stopped, false)
    if (kind === 'research') {
      assert.deepEqual(result.returned.map(row => row.assignment_id), h.starts.map(i => `assignment-${i}`))
    }
    for (const { prompt } of h.calls.filter(call => call.options.phase === 'Workers')) {
      assert.ok(prompt.startsWith('Your FIRST operation'))
      assert.match(prompt, /fanout_dispatch\.py start --ticket/)
      assert.match(prompt, /fanout_dispatch\.py finish --ticket/)
    }
    assert.match(h.verifyPrompt, /fanout_dispatch\.py reconcile/)
    assert.match(h.verifyPrompt, /can_close true/)
    assert.match(h.verifyPrompt, /fanout_dispatch\.py close-session/)
  })

  for (const [label, target, args] of [
    ['fixed', 2, { concurrency: 2, capacity: 8 }],
    ['adaptive checkpoint', 8, { capacity: 8 }],
    ['lower host capacity', 3, { capacity: 3 }],
  ]) {
    await test(`${kind}: ${label} bound`, async () => {
      const h = await host(kind, { target, args })
      await h.drain()
      assert.equal(h.peak, target)
      assert.match(h.calls[0].prompt, new RegExp(`--capacity ${args.capacity}`))
      if (args.concurrency) assert.match(h.calls[0].prompt, /--concurrency 2/)
    })
  }

  await test(`${kind}: legacy waves retain their barrier and old arguments`, async () => {
    const h = await host(kind, { mode: 'legacy', args: { concurrency: 6 } })
    await h.finish(1)
    assert.equal(h.starts.length, 6)
    for (const index of [2, 3, 4, 5]) await h.finish(index)
    assert.equal(h.starts.length, 6)
    await h.finish(0)
    assert.equal(h.starts.length, 12)
    await h.drain()
    assert.doesNotMatch(h.calls.find(call => call.options.phase === 'Workers').prompt, /start --ticket/)
    assert.doesNotMatch(h.verifyPrompt, /fanout_dispatch\.py reconcile/)
  })

  for (const errorMode of ['null', 'rejected', 'mismatched']) {
    await test(`${kind}: ${errorMode} worker stops admission and keeps evidence private`, async () => {
      const h = await host(kind)
      if (errorMode === 'rejected') await h.reject(1)
      else await h.finish(1, errorMode === 'null' ? null : { assignment_id: 'wrong' })
      assert.equal(h.starts.length, 6)
      const result = await h.drain()
      assert.equal(result.admission_stopped, true)
      assert.equal(h.starts.length, 6)
      assert.match(h.verifyPrompt, /--stop-admissions/)
      assert.doesNotMatch(h.verifyPrompt, /--throttled|--retry-after-seconds/)
      assert.ok(h.logs.every(line => !line.includes('SECRET_SUBSTANTIVE_LABEL')))
    })
  }

  await test(`${kind}: empty queue and maximum queue reserve controller calls`, async () => {
    const empty = await host(kind, { count: 0 })
    await empty.drain()
    assert.equal(empty.starts.length, 0)
    const max = await host(kind, { count: 998, args: { limit: 2000 } })
    await max.drain()
    assert.equal(max.calls.length, 1000)
    assert.match(max.calls[0].prompt, /--limit 998/)
  })

  for (const [label, config] of [
    ['missing owner', { args: { owner: null } }],
    ['malformed owner', { args: { owner: { incorrect: true } } }],
    ['mismatched owner', { discovery: { owner: 'another-owner' } }],
    ['reopened session', { discovery: { reused_session: true } }],
    ['paused session', { discovery: { state: 'paused' } }],
    ['oversized discovery', { count: 999 }],
    ['target exceeds capacity', { target: 7, args: { capacity: 6 } }],
    ['target exceeds explicit concurrency', { target: 7, args: { concurrency: 6, capacity: 8 } }],
    ['duplicate ticket', { count: 2, discovery: { tickets: [item(0), item(0)] } }],
    ['duplicate assignment', { count: 2, discovery: { tickets: [item(0), { ...item(0), ticket_id: 'different-ticket' }] } }],
  ]) {
    await test(`${kind}: ${label} fails before worker launch`, async () => {
      const h = await host(kind, config)
      assert.ok(h.done)
      assert.ok(h.failure)
      assert.equal(h.starts.length, 0)
    })
  }

  await test(`${kind}: native extra-property stringification preserves typed control fields`, async () => {
    const h = await host(kind, { count: 3, target: 2, nativeExtraStrings: true })
    assert.equal((await h.drain()).admission_stopped, false)
    assert.equal(h.starts.length, 3)
    assert.equal(h.peak, 2)
  })

  await test(`${kind}: structured discovery failure surfaces safely before batch validation`, async () => {
    const h = await host(kind, { discovery: {
      mode: 'failed', status: 'discovery_failure', error: 'dispatch_failed_closed', tickets: undefined,
      note: 'SECRET_SUBSTANTIVE_LABEL',
    } })
    assert.ok(h.done)
    assert.match(String(h.failure), /Dispatch discovery failed closed/)
    assert.doesNotMatch(String(h.failure), /oversized|SECRET_SUBSTANTIVE_LABEL/)
    assert.equal(h.starts.length, 0)
  })

  await test(`${kind}: missing final dispatch evidence cannot report success`, async () => {
    const h = await host(kind, { count: 1, verification: { dispatch: null } })
    await assert.rejects(h.drain(), /Dispatch finality was not verified/)
  })

  await test(`${kind}: failed close cannot report a closed session`, async () => {
    const h = await host(kind, { count: 1, verification: {
      dispatch: { reconciliation: { can_close: true }, close: { error: 'dispatch_failed_closed' } },
    } })
    await assert.rejects(h.drain(), /Dispatch finality was not verified/)
  })

  await test(`${kind}: authorized migration resume reaches the first open-session call`, async () => {
    const h = await host(kind, { count: 1, args: {
      resume_request: '/fixture/resume-request.json', request_root: '/fixture/project',
    } })
    await h.drain()
    assert.match(h.calls[0].prompt, /--request '\/fixture\/resume-request\.json'/)
    assert.match(h.calls[0].prompt, /--request-root '\/fixture\/project'/)
    assert.doesNotMatch(h.verifyPrompt, /--request /)
  })
}

await test('coding: canonical worker_error remains a terminal unit failure', async () => {
  const h = await host('coding')
  await h.finish(1, { assignment_id: 'assignment-1', unit_id: 'unit-1', status: 'worker_error',
    output_path: '/fixture/returns/1.json', sha256: 'b'.repeat(64) })
  assert.ok(h.starts.includes(6))
  assert.equal((await h.drain()).admission_stopped, false)
})

await test('research: incomplete return stops admissions for reconciliation without retry', async () => {
  const h = await host('research')
  await h.finish(1, { assignment_id: 'assignment-1', attempt: 1, output_path: '/fixture/returns/1.json',
    complete: false, summary: 'incomplete' })
  assert.equal((await h.drain()).admission_stopped, true)
  assert.equal(h.starts.filter(index => index === 1).length, 1)
})

await test('research: a source access gap is not provider throttle evidence', async () => {
  const h = await host('research')
  await h.finish(1, { assignment_id: 'assignment-1', attempt: 1, output_path: '/fixture/returns/1.json',
    complete: true, summary: 'one source returned HTTP 429 Retry-After: 60; access gap recorded', sha256: 'a'.repeat(64) })
  assert.ok(h.starts.includes(6))
  assert.equal((await h.drain()).admission_stopped, false)
  assert.doesNotMatch(h.verifyPrompt, /--throttled|--retry-after-seconds/)
})

await test('saved arguments preserve model/effort and shell literals', async () => {
  const weirdPath = "/fixture's/$(never-execute)`literal"
  const h = await host('research', { count: 1, args: {
    fanout_dir: weirdPath, owner: "session's-owner", model: 'fixture-model', effort: 'high',
  } })
  await h.drain()
  assert.ok(h.calls[0].prompt.includes("'/fixture'\\''s/$(never-execute)`literal'"))
  assert.equal(h.calls.find(call => call.options.phase === 'Workers').options.model, 'fixture-model')
  assert.equal(h.calls.find(call => call.options.phase === 'Workers').options.effort, 'high')
})

process.stdout.write(`${passed} saved-workflow execution checks passed\n`)
