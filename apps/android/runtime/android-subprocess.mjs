// Reviewed fixed-command adapter for the original SubprocessRuntime service.
// No generic command, raw pipe, spill, environment forwarding or PTY support.
import { AsyncLocalStorage } from 'node:async_hooks';
import { createRequire } from 'node:module';
import { brokerRequest } from './command-wire.mjs';
const resolveCli = createRequire(new URL('../../../packages/subprocess/subprocess-local/package.json', import.meta.url));
const { SubprocessRuntime, SubprocessError, SubprocessExecutableNotFoundError } = await import(resolveCli.resolve('@deepseek-ai/dsh-subprocess'));
const calls = new AsyncLocalStorage();
const failure = (message, code = 'SUBPROCESS_SPAWN_FAILED') => new SubprocessError(message, code);
export function withFixedPwdCall(fields, action) {
  if (fields.executable !== '/system/bin/pwd' || fields.arguments.length || !fields.sessionId || !fields.callId) throw failure('Invalid fixed call binding');
  return calls.run(Object.freeze({ ...fields, arguments: Object.freeze([]) }), action);
}
function reader(maxBytes) {
  let bytes = Buffer.alloc(0), total = 0;
  return {
    put(text) { const complete = Buffer.from(text); total = complete.length; bytes = complete.subarray(Math.max(0, total - maxBytes)); },
    readFrom(fromByte) {
      if (!Number.isSafeInteger(fromByte) || fromByte < 0) throw failure('Invalid collected-output offset');
      const start = total - bytes.length;
      return { text: bytes.subarray(Math.max(0, fromByte - start)).toString('utf8'), nextOffset: total, lossy: fromByte < start };
    },
  };
}
async function waitBounded(promise, signal) {
  if (signal?.aborted) return false;
  if (!signal) { await promise; return true; }
  let abort;
  const stopped = new Promise(resolve => { abort = () => resolve(false); signal.addEventListener('abort', abort, { once: true }); });
  try { return await Promise.race([promise.then(() => true), stopped]); }
  finally { signal.removeEventListener('abort', abort); }
}
export class AndroidFixedPwdSubprocess extends SubprocessRuntime {
  constructor(ctx) {
    super(ctx);
    this.active = new Set(); this.disposed = false; this.cleanupFailures = [];
    ctx.effect(() => async () => {
      this.disposed = true;
      const active = [...this.active];
      for (const handle of active) handle.terminate();
      const settled = await Promise.allSettled(active.map(handle => handle.waitForExit()));
      const errors = [...this.cleanupFailures, ...settled.filter(item => item.status === 'rejected').map(item => item.reason)];
      if (errors.length) throw new AggregateError(errors, 'Native subprocess quiescence not established');
    }, 'android fixed subprocess teardown');
  }
  async resolveExecutable(command, env, signal) {
    signal?.throwIfAborted();
    if (env && Object.keys(env).length) throw failure('Environment overrides are unsupported');
    if (command !== 'pwd' && command !== '/system/bin/pwd') throw new SubprocessExecutableNotFoundError('Only native fixed pwd is available through this adapter');
    const info = await brokerRequest('describe', {}, signal);
    if (!info.ok || info.fixedExecutableAvailable !== true) throw new SubprocessExecutableNotFoundError('Native host did not verify fixed pwd');
    return '/system/bin/pwd';
  }
  async terminalEnvironment(signal) { signal?.throwIfAborted(); return { platform: 'posix' }; }
  async spawnTerminal(spec) {
    spec.signal?.throwIfAborted();
    throw failure('Interactive native PTY transport is not implemented; a passing capability fixture is not a terminal handle', 'SUBPROCESS_PTY_UNAVAILABLE');
  }
  spawn(spec) {
    const signal = spec.signal;
    signal?.throwIfAborted();
    const bound = calls.getStore();
    if (this.disposed || !bound) throw failure('A live original tool-call binding is required');
    if (spec.argv.length !== 1 || spec.argv[0] !== '/system/bin/pwd' || spec.cwd !== bound.cwd) throw failure('Request differs from native fixed call');
    if (spec.env && Object.keys(spec.env).length) throw failure('Environment overrides are unsupported');
    if (spec.graceMs !== 2000) throw failure('Invalid native wait grace');
    if (spec.stdio.stdin !== 'ignore' || spec.stdio.control !== undefined) throw failure('Interactive stdin and control channels are unsupported');
    for (const mode of [spec.stdio.stdout, spec.stdio.stderr]) {
      if (!mode || typeof mode !== 'object' || mode.spill !== undefined || !Number.isSafeInteger(mode.maxBytes) || mode.maxBytes < 1 || mode.maxBytes > 65536) throw failure('Only bounded collected stdout/stderr without spill are supported');
    }
    const stdout = reader(spec.stdio.stdout.maxBytes), stderr = reader(spec.stdio.stderr.maxBytes);
    const cancellation = new AbortController();
    const abort = () => cancellation.abort();
    signal?.addEventListener('abort', abort, { once: true });
    let quiescent = false, observationFailure;
    const done = Promise.resolve().then(async () => {
      if (signal?.aborted) cancellation.abort();
      const reply = await brokerRequest('execute', bound, cancellation.signal);
      if (reply.ok === false && ['USED', 'APPROVAL_REQUIRED', 'REQUEST_CHANGED', 'CLOSED', 'UNAUTHENTICATED', 'MALFORMED'].includes(reply.code)) {
        quiescent = true; const error = failure('Native execution rejected: ' + reply.code); error.nativeCode = reply.code; throw error;
      }
      if (!reply.ok || !reply.result || typeof reply.result.stdout !== 'string' || typeof reply.result.stderr !== 'string'
          || !Number.isSafeInteger(reply.result.exitCode) || reply.result.exitCode < 0 || reply.result.cwd !== bound.cwd) throw failure('Invalid or failed native execution outcome', 'SUBPROCESS_RUNNER_IPC_FAILED');
      quiescent = true; stdout.put(reply.result.stdout); stderr.put(reply.result.stderr);
      if (cancellation.signal.aborted || reply.result.exitCode !== 0) {
        const error = failure('Fixed pwd returned native status ' + reply.result.exitCode + '; normal-exit/signal classification is unavailable for this interrupted or failed qualification', 'SUBPROCESS_RUNNER_FAILED');
        error.nativeExitCode = reply.result.exitCode; throw error;
      }
      return { exitCode: reply.result.exitCode, signal: null };
    }).finally(() => { signal?.removeEventListener('abort', abort); });
    // A rejected RPC may leave the host's outcome unknown. A separate cancel reply
    // must acknowledge native OwnedProcess.close before teardown can claim exit.
    const settled = done.catch(async error => {
      if (!quiescent) {
        try { const reply = await brokerRequest('cancel', bound); if (!reply.ok) throw failure('Native cancellation unacknowledged'); quiescent = true; }
        catch (cleanup) { observationFailure = cleanup; this.cleanupFailures.push(cleanup); }
      }
    });
    const handle = { stdin: undefined, stdout: undefined, stderr: undefined, control: undefined,
      collected: { stdout, stderr }, done,
      terminate() { cancellation.abort(); },
      waitForExit(signal) { return waitBounded(settled.then(() => { if (observationFailure) throw observationFailure; if (!quiescent) throw failure('Native range remains unobserved'); }), signal); },
    };
    this.active.add(handle);
    void settled.finally(() => this.active.delete(handle));
    return handle;
  }
}

export default AndroidFixedPwdSubprocess;
