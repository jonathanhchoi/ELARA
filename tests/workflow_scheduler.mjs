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
    assignment_id: `assignment-${index}`, unit_id: `unit-${index}`, attempt: 1, launches: 1,
    assignment_path: `/fixture/assignments/${index}.json`, draft_path: `/fixture/drafts/${index}.json`,
    brief_path: `/fixture/briefs/${index}.md`, return_path: `/fixture/returns/${index}.json`,
  }
}

async function host(kind, { count = 18, args = {}, discovery = {}, verification = {}, nativeExtraStrings = false,
  discoveryError = null, workerError = null } = {}) {
  const file = `.claude/workflows/elr-${kind === 'coding' ? 'observation' : 'research'}-fanout.js`
  if (!sources.has(file)) sources.set(file, readFile(path.join(root, file), 'utf8'))
  const source = (await sources.get(file)).replace('export const meta =', 'const meta =')
  const items = Array.from({ length: count }, (_, index) => item(index))
  const discovered = {
    expected: count, terminal: 0, complete: 0, exhausted: 0, pending: count, time_box_minutes: 5,
    launches_recorded: count, closed_after_launches: [], pending_assignments: items,
    ...discovery,
  }
  const config = { ...(kind === 'coding' ? { run_dir: '/fixture' } : { fanout_dir: '/fixture' }), ...args }
  const calls = [], logs = [], starts = [], finishes = [], waiting = new Map()
  let active = 0, peak = 0, done = false, outcome, failure, discoverPrompt, verifyPrompt
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
      assert.equal(active, 0, 'a controller step overlapped unfinished workers')
      assert.equal(options.agentType, 'elr-worker')
      if (options.label === 'discover-pending') {
        discoverPrompt = prompt
        if (discoveryError) throw new Error(discoveryError)
        return structured(discovered, options.schema)
      }
      verifyPrompt = prompt
      const status = kind === 'coding'
        ? { expected: count, terminal: finishes.length, invalid: 0, pending: count - finishes.length }
        : { expected: count, complete: finishes.length, incomplete: 0, missing: count - finishes.length,
            invalid: 0, exhausted: 0, pending: count - finishes.length,
            attempt_counts: { attempted: starts.length, succeeded: finishes.length, failed: 0,
              unusable: 0, outstanding: count - finishes.length } }
      return verification === null ? null : structured({ ...status, ...verification }, options.schema)
    }
    assert.equal(options.agentType, kind === 'coding' ? 'elr-worker' : 'elr-research-worker')
    if (workerError) throw new Error(workerError)
    const index = Number(options.label.replace('assignment-', ''))
    assert.ok(!waiting.has(index) && !starts.includes(index), 'assignment launched more than once')
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
    ? { assignment_id: `assignment-${index}`, unit_id: `unit-${index}`, status: 'succeeded',
        output_path: `/fixture/returns/${index}.json`, sha256: 'a'.repeat(64) }
    : { assignment_id: `assignment-${index}`, attempt: 1, output_path: `/fixture/returns/${index}.json`,
        complete: true, summary: 'one completed assignment' }
  return {
    calls, logs, starts, finishes, waiting, config,
    get peak() { return peak }, get done() { return done }, get result() { return outcome },
    get failure() { return failure }, get discoverPrompt() { return discoverPrompt },
    get verifyPrompt() { return verifyPrompt },
    workerPrompts: () => calls.filter(call => call.options.phase === 'Workers').map(call => call.prompt),
    async finish(index, replacement) {
      assert.ok(waiting.has(index), `worker ${index} was not running`)
      waiting.get(index).resolve(replacement === undefined ? receipt(index) : replacement)
      await flush()
    },
    async reject(index, message = 'SECRET_SUBSTANTIVE_LABEL_IN_PROVIDER_ERROR 429 Retry-After: 60') {
      waiting.get(index).reject(new Error(message))
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
  const controllerScript = kind === 'coding' ? 'unit_fanout.py' : 'research_fanout.py'

  await test(`${kind}: rolling pool refills before the slow first worker`, async () => {
    const h = await host(kind)
    assert.deepEqual(h.starts, [0, 1, 2, 3, 4, 5])
    await h.finish(1)
    assert.ok(h.waiting.has(0))
    assert.ok(h.starts.includes(6), 'seventh worker waited for the first wave')
    const result = await h.drain()
    assert.equal(h.peak, 6)
    assert.deepEqual([...h.starts].sort((a, b) => a - b), Array.from({ length: 18 }, (_, i) => i))
    assert.equal(h.calls.length, 20)
    assert.equal(result.verified, true)
    assert.deepEqual(result.no_receipt, [])
    assert.match(h.discoverPrompt, new RegExp(`${controllerScript.replace('.', '\\.')} status .*--record-launch --limit 998`))
    assert.match(h.verifyPrompt, new RegExp(`${controllerScript.replace('.', '\\.')} status`))
    assert.doesNotMatch(h.verifyPrompt, /--record-launch/)
    for (const prompt of h.workerPrompts()) {
      assert.doesNotMatch(prompt, /fanout_dispatch|ticket|observation-fanout\.md/)
      assert.ok(prompt.length < 1200, 'worker prompt is not short')
      if (kind === 'coding') {
        assert.match(prompt, /--input '\/fixture\/drafts\/\d+\.json'/)
        assert.match(prompt, /Write tool/)
      } else {
        assert.match(prompt, /This is attempt 1\./)
        assert.match(prompt, /\/fixture\/returns\/\d+\.json/)
      }
    }
    if (kind === 'research') {
      assert.deepEqual(result.returned.map(row => row.assignment_id).sort(), h.starts.map(i => `assignment-${i}`).sort())
    }
  })

  for (const [label, args, expected] of [
    ['fixed concurrency', { concurrency: 2 }, 2],
    ['concurrency above the runtime ceiling', { concurrency: 40 }, 16],
  ]) {
    await test(`${kind}: ${label}`, async () => {
      const h = await host(kind, { args })
      await h.drain()
      assert.equal(h.peak, expected)
    })
  }

  for (const errorMode of ['null', 'rejected', 'mismatched']) {
    await test(`${kind}: a ${errorMode} worker never stops the batch and keeps evidence private`, async () => {
      const h = await host(kind)
      if (errorMode === 'rejected') await h.reject(1)
      else await h.finish(1, errorMode === 'null' ? null : { assignment_id: 'wrong' })
      assert.ok(h.starts.includes(6), 'the free slot was not refilled')
      const result = await h.drain()
      assert.equal(h.starts.length, 18)
      assert.deepEqual(result.no_receipt, ['assignment-1'])
      assert.ok(h.logs.every(line => !line.includes('SECRET_SUBSTANTIVE_LABEL')))
      assert.ok(JSON.stringify(result).indexOf('SECRET_SUBSTANTIVE_LABEL') === -1)
    })
  }

  await test(`${kind}: empty queue and maximum queue reserve controller calls`, async () => {
    const empty = await host(kind, { count: 0 })
    await empty.drain()
    assert.equal(empty.starts.length, 0)
    assert.equal(empty.calls.length, 2)
    const max = await host(kind, { count: 998, args: { limit: 2000 } })
    await max.drain()
    assert.equal(max.calls.length, 1000)
    assert.match(max.discoverPrompt, /--limit 998/)
  })

  for (const [label, config, pattern] of [
    ['controller error', { discovery: { error: 'ERROR: run manifest does not match run_seal.json' } }, /did not list the pending assignments.*run_seal/],
    ['missing listing', { discovery: { pending_assignments: undefined } }, /did not list the pending assignments/],
    ['malformed item', { count: 1, discovery: { pending_assignments: [{ assignment_id: 'x' }] } }, /malformed/],
    ['oversized listing', { count: 999 }, /more assignments than the limit/],
    ['missing worker type at discovery', { discoveryError: "Agent type 'elr-worker' not found" }, /restart the app there once/],
  ]) {
    await test(`${kind}: ${label} fails before any worker launch`, async () => {
      const h = await host(kind, config)
      assert.ok(h.done)
      assert.match(String(h.failure), pattern)
      assert.equal(h.starts.length, 0)
    })
  }

  await test(`${kind}: a missing worker type stops launching and gives the restart instruction`, async () => {
    const h = await host(kind, { workerError: `Agent type '${kind === 'coding' ? 'elr-worker' : 'elr-research-worker'}' not found` })
    await flush()
    assert.ok(h.done)
    assert.match(String(h.failure), /restart the app there once/)
    assert.ok(h.calls.filter(call => call.options.phase === 'Workers').length <= 6)
  })

  await test(`${kind}: a duplicated listing launches the assignment once`, async () => {
    const h = await host(kind, { count: 2, discovery: { pending_assignments: [item(0), item(0), item(1)] } })
    await h.drain()
    assert.deepEqual([...h.starts].sort(), [0, 1])
  })

  await test(`${kind}: native extra-property stringification preserves typed control fields`, async () => {
    const h = await host(kind, { count: 3, args: { concurrency: 2 }, nativeExtraStrings: true })
    const result = await h.drain()
    assert.equal(h.starts.length, 3)
    assert.equal(h.peak, 2)
    assert.equal(result.verified, true)
  })

  await test(`${kind}: arguments of earlier versions are accepted and ignored`, async () => {
    const h = await host(kind, { count: 2, args: {
      owner: 'native-session', capacity: 8, resume_request: '/fixture/request.json',
      request_root: '/fixture/project', fixture: true, include_exhausted: true,
    } })
    await h.drain()
    for (const call of h.calls) assert.doesNotMatch(call.prompt, /--owner|--capacity|--request|--include-exhausted/)
  })

  await test(`${kind}: an unavailable final status is reported, not thrown`, async () => {
    const h = await host(kind, { count: 2, verification: null })
    const result = await h.drain()
    assert.equal(result.verified, false)
  })
}

await test('coding: already_submitted and worker_error receipts count as receipts', async () => {
  const h = await host('coding')
  await h.finish(1, { assignment_id: 'assignment-1', unit_id: 'unit-1', status: 'worker_error',
    output_path: '/fixture/returns/1.json', sha256: 'b'.repeat(64) })
  await h.finish(2, { assignment_id: 'assignment-2', unit_id: 'unit-2', status: 'already_submitted',
    output_path: '/fixture/returns/2.json', sha256: 'c'.repeat(64) })
  const result = await h.drain()
  assert.deepEqual(result.no_receipt, [])
  assert.equal(result.receipts, 18)
})

await test('coding: block and limit reach the controller', async () => {
  const h = await host('coding', { count: 2, args: { block: 3, limit: 50 } })
  await h.drain()
  assert.match(h.discoverPrompt, /--record-launch --limit 50 --block 3/)
})

await test('research: an incomplete return never stops the batch', async () => {
  const h = await host('research')
  await h.finish(1, { assignment_id: 'assignment-1', attempt: 1, output_path: '/fixture/returns/1.json',
    complete: false, summary: 'incomplete' })
  assert.ok(h.starts.includes(6))
  const result = await h.drain()
  assert.equal(h.starts.length, 18)
  assert.equal(result.returned.find(row => row.assignment_id === 'assignment-1').complete, false)
})

await test('saved arguments preserve model/effort and shell literals', async () => {
  const weirdPath = "/fixture's/$(never-execute)`literal"
  const h = await host('research', { count: 1, args: { fanout_dir: weirdPath, model: 'fixture-model', effort: 'high' } })
  await h.drain()
  assert.ok(h.discoverPrompt.includes("'/fixture'\\''s/$(never-execute)`literal'"))
  const worker = h.calls.find(call => call.options.phase === 'Workers')
  assert.equal(worker.options.model, 'fixture-model')
  assert.equal(worker.options.effort, 'high')
  assert.equal(h.calls[0].options.model, undefined)
  const coding = await host('coding', { count: 1, args: { run_dir: weirdPath } })
  await coding.drain()
  assert.ok(coding.workerPrompts()[0].includes("--run-dir '/fixture'\\''s/$(never-execute)`literal'"))
})

process.stdout.write(`${passed} saved-workflow execution checks passed\n`)
