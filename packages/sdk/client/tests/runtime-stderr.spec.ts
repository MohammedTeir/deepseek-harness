/** Real child stderr transport, not an Android runtime or agent proof. */
import { expect, it } from 'vitest'
import { createProcessHarnessClient } from '../src/client.ts'

it('retains a readable stderr snapshot before launch and after process cleanup', async () => {
  const client = createProcessHarnessClient({
    command: process.execPath,
    args: ['-e', "process.stderr.write('actual runtime diagnostic\\nsecond diagnostic\\n'); process.stdin.resume(); process.stdin.on('end', () => process.exit(0))"],
    environment: () => ({ ...process.env }),
    description: 'stderr transport fixture',
    initializeTimeoutMs: 1000,
    shutdownTimeoutMs: 20,
    disposeEofGraceMs: 1000,
    disposeGraceMs: 500,
  })
  try {
    expect(await client.runtimeStderr()).toBe('')
    client.start()
    await client.close()
    const snapshot = await client.runtimeStderr()
    expect(snapshot).toContain('actual runtime diagnostic\nsecond diagnostic')
    expect(await client.runtimeStderr()).toBe(snapshot)
  } finally { await client.close() }
})
