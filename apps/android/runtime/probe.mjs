/** Candidate-runtime diagnostics only; this does not launch or replace the Harness agent. */
import { mkdtemp, writeFile, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { Worker } from 'node:worker_threads'

const checks = []
async function check(name, run) {
  try { await run(); checks.push({ name, status: 'PASS' }) }
  catch (error) { checks.push({ name, status: 'FAIL', code: error.code ?? error.name }) }
}
await check('required-node-version', () => {
  const [major, minor] = process.versions.node.split('.').map(Number)
  if (major < 24 || (major === 24 && minor < 9)) throw new Error('Node version too old')
})
await check('android-arm64', () => {
  if (process.platform !== 'android' || process.arch !== 'arm64') throw new Error('Not Android ARM64')
})
await check('filesystem-roundtrip', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'dsh-probe-'))
  try {
    await writeFile(join(directory, 'probe'), 'harness')
    if (await readFile(join(directory, 'probe'), 'utf8') !== 'harness') throw new Error('Read mismatch')
  } finally { await rm(directory, { recursive: true, force: true }) }
})
await check('sqlite', async () => {
  const { DatabaseSync } = await import('node:sqlite')
  const db = new DatabaseSync(':memory:')
  try { db.exec('CREATE TABLE probe (value TEXT)'); db.prepare('INSERT INTO probe VALUES (?)').run('ok')
    if (db.prepare('SELECT value FROM probe').get().value !== 'ok') throw new Error('SQLite mismatch')
  } finally { db.close() }
})
await check('worker-thread', () => new Promise((resolve, reject) => {
  const worker = new Worker('require("node:worker_threads").parentPort.postMessage("ready")', { eval: true })
  const timeout = setTimeout(() => { void worker.terminate(); reject(new Error('Worker timeout')) }, 5000)
  worker.once('message', message => { if (message !== 'ready') reject(new Error('Worker mismatch')) })
  worker.once('error', error => { clearTimeout(timeout); reject(error) })
  worker.once('exit', code => { clearTimeout(timeout); if (code === 0) resolve(); else reject(new Error('Worker exit')) })
}))
console.log(JSON.stringify({ schemaVersion: 1, node: process.versions.node, platform: process.platform,
  arch: process.arch, checks, unverified: ['DNS/TLS on device', 'native flock', 'PTY', 'Harness profile boot',
    'authenticated RPC', 'approved agent tool roundtrip', 'restart persistence'] }, null, 2))
if (checks.some(result => result.status === 'FAIL')) process.exitCode = 1
