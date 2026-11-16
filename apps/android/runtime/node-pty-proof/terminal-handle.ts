/// <reference path="../../../../packages/subprocess/subprocess-local/node_modules/node-pty/typings/node-pty.d.ts" />
/** Host-only qualification of the original terminal-process contract; not an Android execution authority. */
import { PassThrough } from 'node:stream'
import { createRequire } from 'node:module'
import { isAbsolute } from 'node:path'
import type { IPty, IPtyForkOptions } from 'node-pty'
import type { SubprocessOutcome, SubprocessTerminalHandle, SubprocessTerminalSignal } from '../../../../packages/subprocess/subprocess/src/types.ts'
const resolver = createRequire(new URL('../../../../packages/subprocess/subprocess-local/package.json', import.meta.url))
const { SubprocessError } = await import(resolver.resolve('@deepseek-ai/dsh-subprocess')) as
  typeof import('../../../../packages/subprocess/subprocess/src/error.ts')

type Factory = { spawn: (file: string, args: string[], options: IPtyForkOptions) => IPty }
type Role = '--tty-child' | '--wait' | '--ignore-term' | '--exit-seven'

/** Fixed-fixture options only; no shell, native approval token or agent-selected program is accepted here. */
export interface FixtureTerminalOptions {
  fixtureExecutable: string
  cwd: string
  role: Role
  graceMs: number
  /** Fixture-owner lifetime signal; not the original spawnTerminal allocation signal. */
  ownerSignal?: AbortSignal
}

const failure = (message: string) => new SubprocessError(message, 'SUBPROCESS_RUNNER_FAILED')

async function within(promise: Promise<void>, milliseconds: number): Promise<boolean> {
  let timer: ReturnType<typeof setTimeout> | undefined
  try {
    const deadline = new Promise<false>((resolve) => { timer = setTimeout(() => resolve(false), milliseconds) })
    return await Promise.race([promise.then(() => true), deadline])
  } finally { clearTimeout(timer) }
}

/**
 * Adapt original node-pty to the original handle for fixed direct-child fixtures on Linux hosts.
 * Android use fails closed: native authorization and the original terminal registry are not wired yet.
 */
export function createFixtureTerminalHandle(pty: Factory, options: FixtureTerminalOptions): SubprocessTerminalHandle {
  if (process.platform !== 'linux') throw new SubprocessError('Linux qualification only', 'SUBPROCESS_PTY_UNAVAILABLE')
  return createHandle(pty, options)
}

/** Reviewed Android qualification only; caller must consume the native exact-request receipt first. */
export function createAndroidFixtureTerminalHandle(pty: Factory, options: FixtureTerminalOptions): SubprocessTerminalHandle {
  if (process.platform !== 'android' || options.role !== '--tty-child') {
    throw new SubprocessError('Only the Android fixed TTY qualification is enabled', 'SUBPROCESS_PTY_UNAVAILABLE')
  }
  return createHandle(pty, options)
}

function createHandle(pty: Factory, options: FixtureTerminalOptions): SubprocessTerminalHandle {
  options.ownerSignal?.throwIfAborted()
  if (!isAbsolute(options.fixtureExecutable) || !isAbsolute(options.cwd)
    || !['--tty-child', '--wait', '--ignore-term', '--exit-seven'].includes(options.role)
    || !Number.isSafeInteger(options.graceMs) || options.graceMs < 1 || options.graceMs > 10000) throw failure('Invalid fixed fixture request')
  const grace = options.graceMs
  const abortSignal = options.ownerSignal
  const terminal = pty.spawn(options.fixtureExecutable, [options.role], {
    cwd: options.cwd, env: { PATH: '/system/bin', HARNESS_PTY_OWNER_PID: String(process.pid) }, cols: 80, rows: 24, name: 'xterm',
  })
  const output = new PassThrough()
  let exited = false, closing = false, revision = 0, totalBytes = 0
  let providerFailure: Error | undefined
  let resolveOutcome!: (value: SubprocessOutcome) => void
  let rejectOutcome!: (error: unknown) => void
  let resolveExit!: () => void
  let rejectExit!: (error: unknown) => void
  let termination: Promise<void> | undefined
  const done = new Promise<SubprocessOutcome>((resolve, reject) => { resolveOutcome = resolve; rejectOutcome = reject })
  const empty = new Promise<void>((resolve, reject) => { resolveExit = resolve; rejectExit = reject })
  // Keep rejection observable to callers without creating an unhandled rejection before they attach.
  void done.catch(() => {})
  void empty.catch(() => {})
  const dataSubscription = terminal.onData((data) => {
    totalBytes += Buffer.byteLength(data)
    if (totalBytes > 16384) {
      providerFailure = failure('Fixed fixture output exceeded its bound')
      void terminate().catch(() => {})
      return
    }
    revision++
    output.write(data)
  })
  const exitSubscription = terminal.onExit((event) => {
    exited = true; revision++
    dataSubscription.dispose(); exitSubscription.dispose()
    abortSignal?.removeEventListener('abort', abort)
    output.end()
    try {
      try { process.kill(terminal.pid, 0); throw failure('Exited fixture PID remains observable') }
      catch (error) { if ((error as NodeJS.ErrnoException).code !== 'ESRCH') throw error }
      resolveExit()
      const names: Record<number, NodeJS.Signals> = { 1: 'SIGHUP', 2: 'SIGINT', 9: 'SIGKILL', 15: 'SIGTERM' }
      if (event.signal && !names[event.signal]) throw failure('Unknown native signal: ' + event.signal)
      if (providerFailure) throw providerFailure
      resolveOutcome({ exitCode: event.signal ? null : event.exitCode, signal: event.signal ? names[event.signal]! : null })
    } catch (error) { rejectOutcome(error); rejectExit(error) }
  })
  const open = () => { if (closing || exited) throw failure('Fixture terminal is closing or exited') }
  async function terminate(): Promise<void> {
    if (termination) return termination
    closing = true
    termination = (async () => {
      if (!exited) {
        try { terminal.kill('SIGTERM') } catch (error) { providerFailure = error instanceof Error ? error : failure(String(error)) }
        if (!await within(empty, grace)) {
          if (!exited) { try { terminal.kill('SIGKILL') } catch (error) { providerFailure = error instanceof Error ? error : failure(String(error)) } }
          if (!await within(empty, 3000)) throw failure('Fixed child quiescence was not observed after KILL')
        }
      }
      await empty
    })()
    return termination
  }
  const abort = () => { void terminate().catch(() => {}) }
  abortSignal?.addEventListener('abort', abort, { once: true })
  if (abortSignal?.aborted) abort()
  return {
    pid: terminal.pid, output, done,
    async write(data) { open(); if (data !== 'pty-input\n' && data !== '\x03') throw failure('Only fixed qualification input is supported'); revision++; terminal.write(data) },
    async resize(cols, rows) { open(); if (!Number.isSafeInteger(cols) || !Number.isSafeInteger(rows) || cols < 1 || rows < 1 || cols > 1000 || rows > 1000) throw failure('Invalid dimensions'); revision++; terminal.resize(cols, rows) },
    async inspectForeground() { open(); return undefined },
    async inspectActivity() { open(); return { state: 'unknown', revision } },
    async signalForeground(_signal: SubprocessTerminalSignal) { open(); throw new SubprocessError('Foreground group has not been proven; refusing to guess the child PID', 'SUBPROCESS_PTY_UNAVAILABLE') },
    terminate,
  }
}
