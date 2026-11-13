/** Host-only fixed backend for the original owner-scoped registry; no Android authority. */
import { createRequire } from 'node:module'
import { isAbsolute } from 'node:path'
import type { SubprocessTerminalHandle } from '../../../../packages/subprocess/subprocess/src/types.ts'
import type {
  TerminalBackend, TerminalBackendSession, TerminalBackendSpawnSpec, TerminalSendOperation,
  TerminalSendRequest, TerminalSessionStatus,
} from '../../../../packages/terminal/terminal/src/types.ts'
const resolver = createRequire(new URL('../../../../packages/terminal/terminal-bash/package.json', import.meta.url))
const { TerminalError, TerminalBackendCleanupError } = await import(resolver.resolve('@deepseek-ai/dsh-terminal')) as
  typeof import('../../../../packages/terminal/terminal/src/error.ts')

/** Qualification injection points: authorize must resolve before any process allocation. */
export interface FixtureBackendOptions {
  authorize(request: Readonly<TerminalBackendSpawnSpec>, signal: AbortSignal): Promise<void>
  createHandle(request: Readonly<TerminalBackendSpawnSpec>, ownerSignal: AbortSignal): SubprocessTerminalHandle
  startupMs: number
}

function aborted(signal: AbortSignal): Promise<never> {
  return new Promise((_, reject) => {
    if (signal.aborted) reject(signal.reason)
    else signal.addEventListener('abort', () => reject(signal.reason), { once: true })
  })
}

/** Adapt a fixed native input/exit fixture to the original TerminalBackend interface on Linux hosts only. */
export function createFixtureTerminalBackend(options: FixtureBackendOptions): TerminalBackend {
  if (process.platform !== 'linux') throw new TerminalError('No Android terminal authority is installed', 'INIT_REJECTED')
  const { authorize, createHandle, startupMs } = options
  if (!Number.isSafeInteger(startupMs) || startupMs < 1 || startupMs > 10000
    || typeof authorize !== 'function' || typeof createHandle !== 'function') {
    throw new TerminalError('Invalid fixed backend configuration', 'INIT_REJECTED')
  }
  return {
    type: 'android-fixture-host',
    async spawn(spec) {
      const allocationSignal = spec.signal
      allocationSignal?.throwIfAborted()
      if (spec.type !== 'android-fixture-host' || typeof spec.cwd !== 'string' || !isAbsolute(spec.cwd)) {
        throw new TerminalError('An explicit fixed workspace is required', 'INIT_REJECTED')
      }
      const request = Object.freeze({ ...spec })
      const owner = new AbortController()
      const startup = new AbortController()
      const timer = setTimeout(() => startup.abort(new TerminalError('Fixture startup deadline', 'STARTUP_TIMEOUT')), startupMs)
      const abort = () => owner.abort(allocationSignal?.reason)
      allocationSignal?.addEventListener('abort', abort, { once: true })
      const signal = AbortSignal.any([owner.signal, startup.signal])
      let handle: SubprocessTerminalHandle | undefined
      let reading: Promise<void> | undefined
      try {
        await Promise.race([authorize(request, signal), aborted(signal)])
        signal.throwIfAborted()
        handle = createHandle(request, owner.signal)
        const processHandle = handle
        let text = '', truncated = false, state: TerminalSessionStatus = { kind: 'running' }
        let transportFailure: unknown
        const ready = Promise.withResolvers<void>()
        const exit = processHandle.done.then((outcome) => {
          state = { kind: 'exited', ...outcome }
          ready.reject(new TerminalError('Fixture exited during startup', 'STARTUP_EXITED'))
          return outcome
        }, (error: unknown) => { transportFailure = error; ready.reject(error); throw error })
        void exit.catch(() => {})
        reading = (async () => {
          for await (const chunk of processHandle.output) {
            text += String(chunk)
            if (Buffer.byteLength(text) > 16384) {
              text = Buffer.from(text).subarray(-16384).toString('utf8'); truncated = true
            }
            if (text.includes('TTY-READY')) ready.resolve()
          }
        })()
        void reading.catch((error: unknown) => {
          transportFailure = error; ready.reject(error)
          void processHandle.terminate().catch(() => {})
        })
        await Promise.race([ready.promise, aborted(signal)])
        signal.throwIfAborted()
        clearTimeout(timer)
        allocationSignal?.removeEventListener('abort', abort)
        const drain = reading
        let closing: Promise<void> | undefined
        let active: TerminalSendOperation | undefined
        const session: TerminalBackendSession = {
          pid: processHandle.pid,
          motd: text,
          status() { if (transportFailure) throw transportFailure; return state },
          startSend(input: TerminalSendRequest) {
            if (closing || state.kind !== 'running') throw new TerminalError('Fixture is closing/exited', 'SESSION_EXITED')
            if (active) throw new TerminalError('Fixture send already active', 'SEND_ACTIVE')
            input.signal?.throwIfAborted()
            if (input.text !== 'pty-input' || input.submit !== true) {
              throw new TerminalError('Only fixed submitted input is allowed', 'INIT_REJECTED')
            }
            const inputSignal = input.signal
            let settled = false, offset = text.length
            let cancellation: Promise<void> | undefined
            const cancel = () => {
              if (settled || state.kind !== 'running' || cancellation) return false
              cancellation = processHandle.write('\x03')
              void cancellation.catch(() => {})
              return true
            }
            const onAbort = () => { cancel() }
            inputSignal?.addEventListener('abort', onAbort, { once: true })
            const done = (async () => {
              await processHandle.resize(100, 40)
              await processHandle.write('pty-input\n')
              const outcome = await exit
              await drain
              if (cancellation) await cancellation
              return { viewport: text, waitReason: 'session_exit' as const,
                sessionStatus: { kind: 'exited' as const, ...outcome }, truncated }
            })().finally(() => { settled = true; active = undefined; inputSignal?.removeEventListener('abort', onAbort) })
            void done.catch(() => {})
            active = {
              done,
              readOutput() { const delta = text.slice(offset); offset = text.length; return { delta, truncated } },
              cancel,
            }
            return active
          },
          read(input) {
            const offset = input.offset ?? 0, requested = input.count ?? 20
            if (!Number.isSafeInteger(offset) || offset < 0 || !Number.isSafeInteger(requested) || requested < 0) {
              throw new TerminalError('Invalid fixed scrollback range', 'INIT_REJECTED')
            }
            const lines = text.split('\n'), count = Math.min(requested, 64)
            const end = Math.max(0, lines.length - offset)
            return { text: lines.slice(Math.max(0, end - count), end).join('\n'), totalLines: lines.length,
              lineBegin: Math.min(offset, lines.length), lineEnd: Math.min(offset + count, lines.length),
              truncated: truncated || requested > 64 }
          },
          async signal(value) { const targetPgid = await processHandle.signalForeground(value); return { delivered: true, targetPgid } },
          close(_reason) {
            if (!closing) {
              owner.abort()
              closing = (async () => {
                const operation = active
                await processHandle.terminate()
                await drain
                if (operation) await Promise.allSettled([operation.done])
              })()
            }
            return closing
          },
        }
        return session
      } catch (error) {
        owner.abort(error)
        try { if (handle) await handle.terminate(); if (reading) await reading }
        catch (cleanup) { throw new TerminalBackendCleanupError(error, cleanup) }
        throw error
      } finally {
        clearTimeout(timer)
        allocationSignal?.removeEventListener('abort', abort)
        startup.abort()
      }
    },
  }
}
