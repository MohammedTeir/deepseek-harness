import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import test from 'node:test'

const observerPath = fileURLToPath(new URL('./web_profile_module_observer.mjs', import.meta.url))

test('module observer records ESM/CJS resolution, realpath, and dlopen without swallowing application errors', () => {
  const root = mkdtempSync(join(tmpdir(), 'dsh-web-module-observer-test-'))
  try {
    const entryPath = join(root, 'entry.mjs')
    const esmPath = join(root, 'child.mjs')
    const cjsPath = join(root, 'child.cjs')
    const invalidAddon = join(root, 'invalid.node')
    const tracePath = join(root, 'module.jsonl')
    writeFileSync(esmPath, 'export const loaded = true\n')
    writeFileSync(cjsPath, 'module.exports = { loaded: true }\n')
    writeFileSync(invalidAddon, 'not an ELF native addon\n')
    writeFileSync(entryPath, [
      "import { realpathSync } from 'node:fs'",
      "import { realpath } from 'node:fs/promises'",
      "import { createRequire } from 'node:module'",
      'const require = createRequire(import.meta.url)',
      "require('./child.cjs')",
      "await import('./child.mjs')",
      "await import('./missing.mjs').catch(() => {})",
      'realpathSync(import.meta.dirname)',
      'await realpath(import.meta.dirname)',
      "try { require('./invalid.node') } catch {}",
      '',
    ].join('\n'))

    const environment = { ...process.env }
    delete environment.NODE_OPTIONS
    environment.ANDROID_WEB_PROFILE_MODULE_TRACE = tracePath
    environment.NODE_OPTIONS = `--import=${pathToFileURL(observerPath).href}`
    const child = spawnSync(process.execPath, [entryPath], {
      cwd: root,
      env: environment,
      encoding: 'utf8',
      timeout: 30_000,
    })
    assert.equal(child.error, undefined, child.error?.message)
    assert.equal(child.status, 0, `${child.stdout}\n${child.stderr}`)

    const records = readFileSync(tracePath, 'utf8').trim().split('\n').map(line => JSON.parse(line))
    assert.ok(records.length > 0)
    assert.ok(records.every(record => record.schemaVersion === 1 && Number.isInteger(record.pid)))
    assert.ok(records.some(record => record.kind === 'resolve' && record.specifier === './child.cjs'))
    assert.ok(records.some(record => record.kind === 'resolve' && record.specifier === './child.mjs'))
    assert.ok(records.some(record => record.kind === 'resolve-failed' && record.specifier === './missing.mjs'))
    assert.ok(records.some(record => record.kind === 'realpath' && record.path === root && record.resolvedPath === root))
    assert.ok(records.some(record => record.kind === 'dlopen' && record.filename === invalidAddon && record.outcome === 'error'))
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
})
