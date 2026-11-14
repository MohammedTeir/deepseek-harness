/** Host-only check of the unchanged built Web profile's boot graph and client bundles. */
import { writeFile } from 'node:fs/promises'
import { expect, it } from 'vitest'
import { parseBootManifest } from '../../../packages/client/modules/src/client/manifest.ts'
import { withDefaultWeb, webGet } from '../../cli/tests/profiles/web/tests/default-web-process.ts'

it('serves the original authenticated boot graph and its advertised client batches', async (test) => {
  await withDefaultWeb(test, async ({ url }) => {
    const initial = await webGet(url, test.signal)
    const cookie = initial.headers['set-cookie']?.[0]?.split(';', 1)[0]
    expect(cookie).toBeDefined()
    const page = await webGet(new URL('/', url), test.signal, { cookie: cookie })
    expect(page.status).toBe(200)
    expect(page.text).toContain('__ModuleLoader__')
    const encoded = /globalThis\["__DSH_BOOT__"\] = ([\s\S]*?)<\/script>/u.exec(page.text)?.[1]
    expect(encoded).toBeDefined()
    const graph = JSON.parse(encoded)
    parseBootManifest(graph)
    const api = new URL('/api/settings/describe', url)
    const withoutCookie = await webGet(api, test.signal)
    const appassetsOrigin = await webGet(api, test.signal, { cookie, origin: 'https://appassets.androidplatform.net' })
    const foreignOrigin = await webGet(api, test.signal, { cookie, origin: 'https://attacker.example' })
    expect(withoutCookie.status).toBe(401)
    expect(appassetsOrigin.status).toBe(403)
    expect(foreignOrigin.status).toBe(403)
    expect(graph.entries.length).toBeGreaterThan(0)
    expect(graph.batches.length).toBeGreaterThan(0)
    const entries = new Set(graph.entries.map(entry => entry.id))
    expect(entries.size).toBe(graph.entries.length)
    const batched = []
    const batches = []
    for (const batch of graph.batches) {
      expect(batch.entries.length).toBeGreaterThan(0)
      expect(batch.entries.every(id => entries.has(id))).toBe(true)
      batched.push(...batch.entries)
      const target = new URL(batch.url, url)
      expect(target.origin).toBe(new URL(url).origin)
      expect(target.pathname.startsWith('/plugins/')).toBe(true)
      const response = await webGet(target, test.signal, { cookie: cookie })
      expect(response.status).toBe(200)
      expect(response.text.length).toBeGreaterThan(0)
      batches.push({ entries: batch.entries.length, status: response.status, bytes: Buffer.byteLength(response.text) })
    }
    expect(batched.length).toBe(graph.entries.length)
    expect(new Set(batched).size).toBe(entries.size)
    if (process.env.ANDROID_WEB_BOOT_HOST_EVIDENCE) {
      await writeFile(process.env.ANDROID_WEB_BOOT_HOST_EVIDENCE, JSON.stringify({ schemaVersion: 1,
        environment: 'Linux host; original built web profile with test-only roster observer; no Android execution',
        frontendBootstrapInjected: true, entries: graph.entries.length, batches,
        originalHostApiRejections: { withoutCookie: withoutCookie.status, appassetsOrigin: appassetsOrigin.status, foreignOrigin: foreignOrigin.status }, backendConnectedOnAndroid: false,
        webViewExecutedOnAndroid: false, gate4Passed: false }, null, 2) + '\n')
    }
  })
})
