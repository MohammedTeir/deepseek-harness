/** Host-only original Web composition with selected platform providers disabled. */
import { writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { FiberState } from '../../../vendor/cordis/src/fiber.ts'
import { expect, it } from 'vitest'
import { parseBootManifest } from '../../../packages/client/modules/src/client/manifest.ts'
import { withDefaultWeb, webGet } from '../../cli/tests/profiles/web/tests/default-web-process.ts'

const patch = fileURLToPath(new URL('./fixtures/web-host-bounded.patch.yml', import.meta.url))
const disabled = {
  subprocess: '@deepseek-ai/dsh-subprocess-local',
  'bash-sandbox': '@deepseek-ai/dsh-bash-sandbox',
  'pwsh-sandbox': '@deepseek-ai/dsh-pwsh-sandbox',
  'open-in-app': '@deepseek-ai/dsh-host-open-in-app',
  'directory-picker': '@deepseek-ai/dsh-host-directory-picker-auto',
  'mcp-manager': '@deepseek-ai/dsh-mcp-manager',
}
it('boots the original Web profile with the explicit host-only platform overlay', async (test) => {
  await withDefaultWeb(test, async ({ url, request }) => {
    const initial = await webGet(url, test.signal)
    const cookie = initial.headers['set-cookie']?.[0]?.split(';', 1)[0]
    expect(cookie).toBeDefined()
    const page = await webGet(new URL('/', url), test.signal, { cookie })
    expect(page.status).toBe(200)
    const encoded = /globalThis\["__DSH_BOOT__"\] = ([\s\S]*?)<\/script>/u.exec(page.text)?.[1]
    expect(encoded).toBeDefined()
    const graph = JSON.parse(encoded)
    parseBootManifest(graph)
    expect(graph.entries.length).toBeGreaterThan(0)
    const roster = await request('roster')
    for (const [id, packageName] of Object.entries(disabled)) {
      const row = roster.entries.find(entry => entry.id === `include:${id}`)
      expect(row, `Expected overlay row ${id}`).toBeDefined()
      expect(row.name).toBe(packageName)
      expect(row.state, `Expected ${id} to be disabled`).toBeUndefined()
    }
    const clientOpenInApp = roster.entries.find(entry => entry.id === 'include:ui-open-in-app')
    expect(clientOpenInApp?.state).toBe(FiberState.ACTIVE)
    expect(roster.client).toEqual(graph)
    const api = new URL('/api/settings/describe', url)
    const noCookie = await webGet(api, test.signal)
    const appassets = await webGet(api, test.signal, { cookie, origin: 'https://appassets.androidplatform.net' })
    const foreign = await webGet(api, test.signal, { cookie, origin: 'https://attacker.example' })
    expect([noCookie.status, appassets.status, foreign.status]).toEqual([401, 403, 403])
    for (const batch of graph.batches) {
      const target = new URL(batch.url, url)
      expect(target.origin).toBe(new URL(url).origin)
      expect(target.pathname.startsWith('/plugins/')).toBe(true)
      const response = await webGet(target, test.signal, { cookie })
      expect(response.status).toBe(200)
      expect(response.text.length).toBeGreaterThan(0)
    }
    if (process.env.ANDROID_WEB_BOUNDED_HOST_EVIDENCE) {
      await writeFile(process.env.ANDROID_WEB_BOUNDED_HOST_EVIDENCE, JSON.stringify({ schemaVersion: 1,
        scope: 'Linux host original Web profile with host-only disabled-service overlay and test roster observer',
        disabledRows: disabled, apiRejections: { noCookie: noCookie.status, appassetsOrigin: appassets.status, foreignOrigin: foreign.status }, bootEntries: graph.entries.length, bootBatches: graph.batches.length,
        clientOpenInAppEntryActive: true, clientBehaviorVerified: false, runtimeSecurityBoundary: false, modelRequestExecuted: false, androidExecuted: false, gate4Passed: false,
      }, null, 2) + '\n')
    }
  }, { patches: [patch] })
})
